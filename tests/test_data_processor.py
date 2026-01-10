import os
import shutil
import tempfile
import gzip
import zipfile
import unittest
import pandas as pd
import polars as pl
from io import BytesIO
import data_processor

class TestDataProcessor(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_gzip_extraction_and_conversion(self):
        # Create a dummy csv
        df = pd.DataFrame({'a': range(100), 'b': range(100)})
        csv_content = df.to_csv(index=False).encode('utf-8')

        # Gzip it
        buf = BytesIO()
        with gzip.open(buf, 'wb') as f:
            f.write(csv_content)
        buf.seek(0)
        buf.name = "test_data.csv.gz"

        # Process
        parquet_files = data_processor.extract_and_convert(
            buf,
            "test_data.csv.gz",
            self.test_dir,
            progress_callback=lambda x: None
        )

        self.assertTrue(len(parquet_files) > 0)
        # Verify parquet content
        df_read = pl.read_parquet(parquet_files[0])
        self.assertEqual(df_read.shape[0], 100)

    def test_zip_extraction_and_conversion(self):
        # Create a dummy csv
        df = pd.DataFrame({'x': range(50), 'y': range(50)})
        csv_content = df.to_csv(index=False).encode('utf-8')

        # Zip it
        buf = BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('data.csv', csv_content)
        buf.seek(0)

        # Process
        parquet_files = data_processor.extract_and_convert(
            buf,
            "archive.zip",
            self.test_dir,
            progress_callback=lambda x: None
        )

        self.assertTrue(len(parquet_files) > 0)
        df_read = pl.read_parquet(parquet_files[0])
        self.assertEqual(df_read.shape[0], 50)

    def test_splitting_large_files(self):
        # Create a csv larger than chunk size
        # We'll set chunk_size small for testing
        df = pd.DataFrame({'col': range(100)})
        csv_content = df.to_csv(index=False).encode('utf-8')

        buf = BytesIO()
        with gzip.open(buf, 'wb') as f:
            f.write(csv_content)
        buf.seek(0)
        buf.name = "large.csv.gz"

        parquet_files = data_processor.extract_and_convert(
            buf,
            "large.csv.gz",
            self.test_dir,
            progress_callback=lambda x: None,
            chunk_size=30 # Should split into 4 files (30, 30, 30, 10)
        )

        self.assertTrue(len(parquet_files) >= 4)
        total_rows = sum(pl.read_parquet(f).height for f in parquet_files)
        self.assertEqual(total_rows, 100)

if __name__ == '__main__':
    unittest.main()
