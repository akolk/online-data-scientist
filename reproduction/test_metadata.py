
import os
import shutil
import tempfile
import data_processor
import polars as pl

def test_metadata_extraction():
    # Setup
    temp_dir = tempfile.mkdtemp()

    # Create a dummy CSV
    csv_content = b"a,b,c\n1,2,3\n4,5,6"
    csv_path = os.path.join(temp_dir, "test.csv")
    with open(csv_path, "wb") as f:
        f.write(csv_content)

    # Convert to Parquet manually (simulating what extract_and_convert does internally)
    df = pl.read_csv(csv_path)
    parquet_path = os.path.join(temp_dir, "test.parquet")
    df.write_parquet(parquet_path)

    parquet_files = [parquet_path]

    # Test get_dataset_info
    info = data_processor.get_dataset_info(parquet_files)
    print(f"Info: {info}")

    # Cleanup
    shutil.rmtree(temp_dir)

    expected = "Schema: a (Int64), b (Int64), c (Int64)"
    if expected in info:
        print("Success!")
    else:
        print(f"Failed. Expected to contain '{expected}'")

if __name__ == "__main__":
    test_metadata_extraction()
