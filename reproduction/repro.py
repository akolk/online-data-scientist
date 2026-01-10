import data_processor
import zipfile
import pandas as pd
import io
import os
import shutil
import tempfile

def run():
    print("Creating test zip...")
    # Create valid CSV
    df = pd.DataFrame({'a': range(10), 'b': range(10)})
    csv_bytes = df.to_csv(index=False).encode('utf-8')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('data.csv', csv_bytes)
    buf.seek(0)
    buf.name = "test.zip"

    tmp_dir = tempfile.mkdtemp()
    print(f"Processing in {tmp_dir}")
    try:
        files = data_processor.extract_and_convert(buf, "test.zip", tmp_dir, lambda x: print(f"Progress: {x}"))
        print(f"Result files: {files}")
    finally:
        shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    run()
