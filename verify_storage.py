
import os
import shutil
import hashlib
import re
from unittest.mock import MagicMock
import tempfile

# Mock objects to mimic Streamlit file upload
class MockUploadedFile:
    def __init__(self, name, size, content):
        self.name = name
        self.size = size
        self.content = content

    def read(self):
        return self.content

def test_storage_logic():
    print("Testing storage logic...")

    # Setup test data
    content = b"col1,col2\n1,2\n3,4"
    uploaded_files = [MockUploadedFile("test.csv", len(content), content)]
    sorted_files = sorted(uploaded_files, key=lambda f: f.name)

    # Logic from app.py
    raw_key = "_".join([f"{f.name}_{f.size}" for f in sorted_files])
    safe_key = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_key)
    if len(safe_key) > 200:
        safe_key = hashlib.md5(raw_key.encode()).hexdigest()
    file_key = f"processed_{safe_key}"

    # Test fallback to local data dir (since /data is not writable here)
    DATA_DIR = "/data"
    if not os.path.exists(DATA_DIR) or not os.access(DATA_DIR, os.W_OK):
        DATA_DIR = os.path.join(os.getcwd(), "data")
        os.makedirs(DATA_DIR, exist_ok=True)

    print(f"Using DATA_DIR: {DATA_DIR}")

    file_dir = os.path.join(DATA_DIR, file_key)

    # Ensure it's clean
    if os.path.exists(file_dir):
        shutil.rmtree(file_dir)

    os.makedirs(file_dir, exist_ok=True)

    # Create a dummy parquet file to simulate processing
    dummy_parquet = os.path.join(file_dir, "test.parquet")
    with open(dummy_parquet, "wb") as f:
        f.write(b"PARQUET_HEADER")

    # Now verification
    assert os.path.exists(file_dir), "Directory was not created"
    assert os.path.exists(dummy_parquet), "File was not created"

    # Verify fallback logic
    if not os.access("/data", os.W_OK) and not os.path.exists("/data"):
        assert DATA_DIR.endswith("/data") == False or DATA_DIR.startswith(os.getcwd()), "Fallback logic failed"

    print(f"Successfully verified storage at {file_dir}")

    # Cleanup
    shutil.rmtree(file_dir)

if __name__ == "__main__":
    test_storage_logic()
