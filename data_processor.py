import os
import zipfile
import gzip
import shutil
import polars as pl
import logging
from typing import List, Optional, Callable
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

# Constants for performance optimization
CHUNK_SIZE_BYTES = 1024 * 1024  # 1MB chunks for file I/O
SAMPLE_SIZE_BYTES = 8192  # 8KB sample for separator detection
PROGRESS_THROTTLE_INTERVAL = 0.1  # Minimum seconds between progress callbacks


@lru_cache(maxsize=128)
def detect_separator(filename: str) -> str:
    """Detect CSV separator by analyzing file sample.

    Uses caching to avoid re-reading files that have already been analyzed.
    Cache key is the filename, so modifications to the file won't be detected
    unless the filename changes.

    Args:
        filename: Path to the CSV file to analyze

    Returns:
        The detected separator character (',' or ';')
    """
    try:
        with open(filename, 'rb') as f:
            # Read sample for separator detection
            sample = f.read(SAMPLE_SIZE_BYTES)
            if not sample:
                return ','  # Default for empty files

            # Count potential separators in the sample
            n_commas = sample.count(b',')
            n_semicolons = sample.count(b';')
            n_tabs = sample.count(b'\t')

            # Return the most frequent separator
            counts = [(n_commas, ','), (n_semicolons, ';'), (n_tabs, '\t')]
            counts.sort(reverse=True)
            return counts[0][1]
    except (IOError, OSError) as e:
        logger.warning(f"Could not detect separator for {filename}: {e}")
        return ','  # Safe default


def get_dataset_info(parquet_files: List[str]) -> str:
    """
    Returns metadata about the dataset (schema, row count estimate from first file).
    Assumes all parquet files belong to the same dataset or at least shares the schema of the first one.
    """
    if not parquet_files:
        return "No data available."

    try:
        # We'll just look at the first file for schema
        lf = pl.scan_parquet(parquet_files[0])
        schema = lf.collect_schema()
        schema_str = ", ".join([f"{k} ({v})" for k, v in schema.items()])

        return f"Schema: {schema_str}"
    except Exception as e:
        return f"Error reading schema: {e}"


class ThrottledProgress:
    """Helper class to throttle progress callback invocations.

    Reduces UI overhead by limiting how frequently progress updates are sent.
    """

    def __init__(self, callback: Optional[Callable[[float], None]], min_interval: float = PROGRESS_THROTTLE_INTERVAL):
        self.callback = callback
        self.min_interval = min_interval
        self.last_call = 0
        self.last_progress = -1.0

    def __call__(self, progress: float):
        """Call the progress callback if enough time has passed or progress is final."""
        if not self.callback:
            return

        import time
        now = time.time()

        # Always call for start (0.0) and end (1.0), or if enough time passed
        if progress in (0.0, 1.0) or (now - self.last_call >= self.min_interval and abs(progress - self.last_progress) >= 0.01):
            self.callback(progress)
            self.last_call = now
            self.last_progress = progress


def _copy_file_chunked(source, target_path: str, progress_callback: Optional[Callable[[float], None]] = None, total_size: int = 0) -> int:
    """Copy file using chunked reading for memory efficiency.

    Args:
        source: File-like object to read from
        target_path: Path to write to
        progress_callback: Optional progress callback
        total_size: Total size for progress calculation (0 = unknown)

    Returns:
        Number of bytes written
    """
    bytes_written = 0
    throttle = ThrottledProgress(progress_callback)

    with open(target_path, "wb") as target:
        while True:
            chunk = source.read(CHUNK_SIZE_BYTES)
            if not chunk:
                break
            target.write(chunk)
            bytes_written += len(chunk)

            if total_size > 0:
                throttle((bytes_written / total_size) * 0.5)

    return bytes_written


def extract_and_convert(
    file_obj,
    filename: str,
    output_dir: str,
    progress_callback: Optional[Callable[[float], None]] = None,
    chunk_size: int = 500000
) -> List[str]:
    """
    Extracts a zip/gzip file and converts it to Parquet in chunks.

    Args:
        file_obj: The file-like object (BytesIO) from Streamlit.
        filename: The original filename.
        output_dir: Directory to store output files.
        progress_callback: Function accepting a float (0.0 to 1.0) for progress.
        chunk_size: Number of rows per batch for Parquet splitting.

    Returns:
        List of paths to the generated Parquet files.
    """
    os.makedirs(output_dir, exist_ok=True)
    extracted_files = []
    throttle = ThrottledProgress(progress_callback)

    # 1. Extraction Phase
    throttle(0.05)

    try:
        if filename.endswith('.zip'):
            with zipfile.ZipFile(file_obj) as zf:
                total_size = sum(info.file_size for info in zf.infolist() if not info.is_dir())
                processed_size = 0

                for info in zf.infolist():
                    if info.is_dir():
                        continue

                    target_path = os.path.join(output_dir, info.filename)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)

                    with zf.open(info) as source:
                        processed_size += _copy_file_chunked(
                            source, target_path,
                            lambda p: throttle(0.05 + p * 0.45),
                            total_size
                        )

                    extracted_files.append(target_path)

        elif filename.endswith('.gz') or filename.endswith('.gzip'):
            out_name = filename.replace('.gz', '').replace('.gzip', '')
            if out_name == filename:
                out_name = "extracted_data.csv"

            target_path = os.path.join(output_dir, out_name)

            with gzip.open(file_obj, 'rb') as source:
                _copy_file_chunked(source, target_path, lambda p: throttle(0.05 + p * 0.45))

            extracted_files.append(target_path)

        elif filename.endswith('.csv'):
            target_path = os.path.join(output_dir, filename)
            # Use chunked reading for memory efficiency with large files
            _copy_file_chunked(file_obj, target_path, lambda p: throttle(0.05 + p * 0.45))
            extracted_files.append(target_path)

        else:
            # Fallback for other files, assuming they are readable as text/csv
            target_path = os.path.join(output_dir, filename)
            # Use chunked reading for memory efficiency
            _copy_file_chunked(file_obj, target_path, lambda p: throttle(0.05 + p * 0.45))
            extracted_files.append(target_path)

    except Exception as e:
        raise RuntimeError(f"Extraction failed: {e}")

    throttle(0.5)

    # 2. Conversion Phase
    parquet_files = []

    data_files = [f for f in extracted_files if os.path.isfile(f) and not os.path.basename(f).startswith('.')]
    total_files = len(data_files)

    for i, source_path in enumerate(data_files):
        try:
            separator = detect_separator(source_path)
            reader = pl.read_csv_batched(source_path, ignore_errors=True, batch_size=chunk_size, separator=separator)

            batch_idx = 0
            file_start_prog = 0.5 + (i / total_files) * 0.5
            file_end_prog = 0.5 + ((i + 1) / total_files) * 0.5

            while True:
                batches = reader.next_batches(1)
                if not batches:
                    # If the first batch is empty, it means the file has no data (or header only)
                    if batch_idx == 0:
                        logger.warning(f"No data found in {source_path}")
                    break

                df = batches[0]

                base_name = os.path.basename(source_path)
                part_name = f"{base_name}.part_{batch_idx}.parquet"
                part_path = os.path.join(output_dir, part_name)

                df.write_parquet(part_path)
                parquet_files.append(part_path)
                batch_idx += 1

                # Simplified progress calculation
                fraction = min(batch_idx / (batch_idx + 10), 0.99)
                current_prog = file_start_prog + (file_end_prog - file_start_prog) * fraction
                throttle(current_prog)

        except Exception as e:
            logger.error(f"Failed to convert {source_path}: {e}")

    throttle(1.0)

    return parquet_files
