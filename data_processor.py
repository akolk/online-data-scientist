import os
import zipfile
import gzip
import shutil
import polars as pl
import time

def extract_and_convert(file_obj, filename, output_dir, progress_callback=None, chunk_size=500000):
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

    # 1. Extraction Phase
    if progress_callback: progress_callback(0.05)

    try:
        if filename.endswith('.zip'):
            with zipfile.ZipFile(file_obj) as zf:
                total_size = sum(info.file_size for info in zf.infolist())
                processed_size = 0

                for info in zf.infolist():
                    if info.is_dir():
                        continue

                    target_path = os.path.join(output_dir, info.filename)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)

                    with zf.open(info) as source, open(target_path, "wb") as target:
                        while True:
                            chunk = source.read(1024 * 1024) # 1MB chunks
                            if not chunk:
                                break
                            target.write(chunk)
                            processed_size += len(chunk)

                            if progress_callback and total_size > 0:
                                progress = (processed_size / total_size) * 0.5
                                progress_callback(progress)

                    extracted_files.append(target_path)

        elif filename.endswith('.gz') or filename.endswith('.gzip'):
            out_name = filename.replace('.gz', '').replace('.gzip', '')
            if out_name == filename:
                out_name = "extracted_data.csv"

            target_path = os.path.join(output_dir, out_name)

            with gzip.open(file_obj, 'rb') as source, open(target_path, 'wb') as target:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
                    if progress_callback: progress_callback(0.25)

            extracted_files.append(target_path)
        else:
            target_path = os.path.join(output_dir, filename)
            with open(target_path, "wb") as target:
                target.write(file_obj.read())
            extracted_files.append(target_path)

    except Exception as e:
        raise RuntimeError(f"Extraction failed: {e}")

    if progress_callback: progress_callback(0.5)

    # 2. Conversion Phase
    parquet_files = []

    data_files = [f for f in extracted_files if os.path.isfile(f) and not os.path.basename(f).startswith('.')]
    total_files = len(data_files)

    for i, source_path in enumerate(data_files):
        try:
            reader = pl.read_csv_batched(source_path, ignore_errors=True, batch_size=chunk_size)

            batch_idx = 0
            while True:
                batches = reader.next_batches(1)
                if not batches:
                    # If the first batch is empty, it means the file has no data (or header only)
                    if batch_idx == 0:
                        print(f"Warning: No data found in {source_path}")
                    break

                df = batches[0]

                base_name = os.path.basename(source_path)
                part_name = f"{base_name}.part_{batch_idx}.parquet"
                part_path = os.path.join(output_dir, part_name)

                df.write_parquet(part_path)
                parquet_files.append(part_path)
                batch_idx += 1

                if progress_callback:
                    file_start_prog = 0.5 + (i / total_files) * 0.5
                    file_end_prog = 0.5 + ((i + 1) / total_files) * 0.5

                    fraction = 1 - (1 / (1 + batch_idx * 0.1))
                    current_prog = file_start_prog + (file_end_prog - file_start_prog) * fraction

                    if current_prog > 0.99: current_prog = 0.99
                    progress_callback(current_prog)

        except Exception as e:
            print(f"Failed to convert {source_path}: {e}")

    if progress_callback: progress_callback(1.0)

    return parquet_files
