import os
import io
import zipfile
import gzip
import tempfile
import shutil
import pytest
import polars as pl
from data_processor import detect_separator, get_dataset_info, extract_and_convert


class TestDetectSeparator:
    """Test suite for detect_separator function."""
    
    def test_detects_comma_separator(self, tmp_path):
        """Test that comma-separated files are detected correctly."""
        csv_file = tmp_path / "comma.csv"
        csv_file.write_text("a,b,c\n1,2,3\n4,5,6")
        
        result = detect_separator(str(csv_file))
        assert result == ","
    
    def test_detects_semicolon_separator(self, tmp_path):
        """Test that semicolon-separated files are detected correctly."""
        csv_file = tmp_path / "semicolon.csv"
        csv_file.write_text("a;b;c\n1;2;3\n4;5;6")
        
        result = detect_separator(str(csv_file))
        assert result == ";"
    
    def test_defaults_to_comma_on_empty_file(self, tmp_path):
        """Test that empty files default to comma separator."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        
        result = detect_separator(str(csv_file))
        assert result == ","
    
    def test_handles_mixed_separators(self, tmp_path):
        """Test that function handles files with both separators (prefers semicolon if more common)."""
        csv_file = tmp_path / "mixed.csv"
        # More semicolons than commas
        csv_file.write_text("a;b;c\n1;2;3\n4;5,6")
        
        result = detect_separator(str(csv_file))
        assert result == ";"


class TestGetDatasetInfo:
    """Test suite for get_dataset_info function."""
    
    def test_returns_no_data_for_empty_list(self):
        """Test that empty parquet list returns appropriate message."""
        result = get_dataset_info([])
        assert result == "No data available."
    
    def test_returns_schema_info_for_valid_parquet(self, tmp_path):
        """Test that schema is extracted from parquet file."""
        # Create a sample parquet file
        parquet_file = tmp_path / "test.parquet"
        df = pl.DataFrame({
            "name": ["Alice", "Bob"],
            "age": [30, 25],
            "salary": [50000.0, 60000.0]
        })
        df.write_parquet(str(parquet_file))
        
        result = get_dataset_info([str(parquet_file)])
        
        assert "Schema:" in result
        assert "name" in result
        assert "age" in result
        assert "salary" in result
    
    def test_handles_multiple_parquet_files(self, tmp_path):
        """Test that function uses first file when multiple provided."""
        parquet_file = tmp_path / "test.parquet"
        df = pl.DataFrame({
            "col1": [1, 2],
            "col2": ["a", "b"]
        })
        df.write_parquet(str(parquet_file))
        
        result = get_dataset_info([str(parquet_file), str(parquet_file)])
        
        assert "Schema:" in result
        assert "col1" in result
        assert "col2" in result
    
    def test_handles_invalid_parquet_gracefully(self, tmp_path):
        """Test that invalid files are handled gracefully."""
        invalid_file = tmp_path / "invalid.parquet"
        invalid_file.write_text("not a parquet file")
        
        result = get_dataset_info([str(invalid_file)])
        
        assert "Error" in result


class TestExtractAndConvert:
    """Test suite for extract_and_convert function."""
    
    def test_extracts_csv_file(self, tmp_path):
        """Test that CSV files are processed correctly."""
        output_dir = tmp_path / "output"
        
        # Create a CSV file in memory
        csv_content = "name,age,city\nAlice,30,NYC\nBob,25,LA"
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        
        result = extract_and_convert(
            file_obj,
            "test.csv",
            str(output_dir),
            progress_callback=None,
            chunk_size=1000
        )
        
        assert len(result) > 0
        assert all(f.endswith('.parquet') for f in result)
        assert all(os.path.exists(f) for f in result)
    
    def test_extracts_gzip_file(self, tmp_path):
        """Test that GZIP files are extracted and converted."""
        output_dir = tmp_path / "output"
        
        # Create a gzipped CSV
        csv_content = "name,age\nAlice,30\nBob,25"
        gzip_buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=gzip_buffer, mode='wb') as gz:
            gz.write(csv_content.encode('utf-8'))
        gzip_buffer.seek(0)
        
        result = extract_and_convert(
            gzip_buffer,
            "test.csv.gz",
            str(output_dir),
            progress_callback=None,
            chunk_size=1000
        )
        
        assert len(result) > 0
        assert all(f.endswith('.parquet') for f in result)
    
    def test_extracts_zip_file(self, tmp_path):
        """Test that ZIP files are extracted and converted."""
        output_dir = tmp_path / "output"
        
        # Create a ZIP file with CSV
        csv_content = "name,age\nAlice,30\nBob,25"
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("data.csv", csv_content)
        zip_buffer.seek(0)
        
        result = extract_and_convert(
            zip_buffer,
            "test.zip",
            str(output_dir),
            progress_callback=None,
            chunk_size=1000
        )
        
        assert len(result) > 0
        assert all(f.endswith('.parquet') for f in result)
    
    def test_splits_large_files_into_chunks(self, tmp_path):
        """Test that large files are split into multiple parquet files."""
        output_dir = tmp_path / "output"
        
        # Create a CSV with many rows
        rows = ["name,age"] + [f"Person{i},{i}" for i in range(100)]
        csv_content = "\n".join(rows)
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        
        result = extract_and_convert(
            file_obj,
            "large.csv",
            str(output_dir),
            progress_callback=None,
            chunk_size=10  # Small chunk size to force splitting
        )
        
        assert len(result) > 1  # Should have multiple parts
        assert all(f.endswith('.parquet') for f in result)
    
    def test_handles_empty_csv(self, tmp_path):
        """Test that empty CSV files are handled gracefully."""
        output_dir = tmp_path / "output"
        
        # Create an empty CSV with just header
        csv_content = "name,age"
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        
        result = extract_and_convert(
            file_obj,
            "empty.csv",
            str(output_dir),
            progress_callback=None,
            chunk_size=1000
        )
        
        # Should handle gracefully - might return empty list or files with just headers
        assert isinstance(result, list)
    
    def test_progress_callback_is_called(self, tmp_path):
        """Test that progress callback is invoked during processing."""
        output_dir = tmp_path / "output"
        progress_calls = []
        
        def progress_callback(progress):
            progress_calls.append(progress)
        
        csv_content = "name,age\nAlice,30\nBob,25"
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        
        extract_and_convert(
            file_obj,
            "test.csv",
            str(output_dir),
            progress_callback=progress_callback,
            chunk_size=1000
        )
        
        assert len(progress_calls) > 0
        assert progress_calls[-1] == 1.0  # Should end at 100%
    
    def test_handles_semicolon_separated_csv(self, tmp_path):
        """Test that semicolon-separated CSV files are handled."""
        output_dir = tmp_path / "output"
        
        csv_content = "name;age\nAlice;30\nBob;25"
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        
        result = extract_and_convert(
            file_obj,
            "semicolon.csv",
            str(output_dir),
            progress_callback=None,
            chunk_size=1000
        )
        
        assert len(result) > 0
        
        # Verify the data was parsed correctly
        df = pl.read_parquet(result[0])
        assert df.shape == (2, 2)
    
    def test_preserves_data_integrity(self, tmp_path):
        """Test that data is preserved correctly during conversion."""
        output_dir = tmp_path / "output"
        
        # Create CSV with various data types
        csv_content = '''name,age,salary,is_active,score
Alice,30,50000.50,true,95.5
Bob,25,60000.75,false,87.2
Charlie,35,75000.00,true,92.1'''
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        
        result = extract_and_convert(
            file_obj,
            "test.csv",
            str(output_dir),
            progress_callback=None,
            chunk_size=1000
        )
        
        assert len(result) > 0
        
        # Read back and verify data
        df = pl.read_parquet(result[0])
        assert df.shape == (3, 5)
        assert df["name"].to_list() == ["Alice", "Bob", "Charlie"]
        assert df["age"].to_list() == [30, 25, 35]
    
    def test_handles_corrupted_zip_gracefully(self, tmp_path):
        """Test that corrupted ZIP files raise appropriate errors."""
        output_dir = tmp_path / "output"
        
        # Create a corrupted ZIP
        corrupted_zip = io.BytesIO(b"not a valid zip file")
        
        with pytest.raises(RuntimeError) as exc_info:
            extract_and_convert(
                corrupted_zip,
                "corrupted.zip",
                str(output_dir),
                progress_callback=None,
                chunk_size=1000
            )
        
        assert "Extraction failed" in str(exc_info.value)
    
    def test_handles_corrupted_gzip_gracefully(self, tmp_path):
        """Test that corrupted GZIP files raise appropriate errors."""
        output_dir = tmp_path / "output"
        
        # Create a corrupted GZIP
        corrupted_gzip = io.BytesIO(b"not a valid gzip file")
        
        with pytest.raises(Exception):
            extract_and_convert(
                corrupted_gzip,
                "corrupted.csv.gz",
                str(output_dir),
                progress_callback=None,
                chunk_size=1000
            )
    
    def test_creates_output_directory_if_not_exists(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        output_dir = tmp_path / "new_output" / "nested"
        
        csv_content = "name,age\nAlice,30"
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        
        result = extract_and_convert(
            file_obj,
            "test.csv",
            str(output_dir),
            progress_callback=None,
            chunk_size=1000
        )
        
        assert os.path.exists(output_dir)
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
