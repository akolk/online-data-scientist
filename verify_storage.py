"""Storage verification utility for testing file persistence logic.

This module provides utilities to test and verify the file storage logic
used in the main application. It includes mock objects for simulating
Streamlit file uploads and functions to verify the storage fallback logic.

Usage:
    Run this module directly to test storage logic:
    $ python verify_storage.py

    Or import the MockUploadedFile class for use in tests:
    >>> from verify_storage import MockUploadedFile
    >>> mock_file = MockUploadedFile("test.csv", 100, b"data")
"""

import os
import shutil
import hashlib
import re
import tempfile

__all__ = [
    "MockUploadedFile",
    "test_storage_logic",
]


class MockUploadedFile:
    """Mock uploaded file object to mimic Streamlit's UploadedFile.

    This class simulates Streamlit's file upload object for testing
    purposes without requiring a Streamlit runtime environment.

    Attributes:
        name: The filename of the uploaded file.
        size: The size of the file content in bytes.
        content: The binary content of the file.

    Example:
        >>> content = b"col1,col2\n1,2\n3,4"
        >>> file = MockUploadedFile("test.csv", len(content), content)
        >>> file.name
        'test.csv'
        >>> file.read()
        b'col1,col2\n1,2\n3,4'
    """

    def __init__(self, name: str, size: int, content: bytes) -> None:
        """Initialize mock uploaded file.

        Args:
            name: The filename.
            size: The size of the content in bytes.
            content: The binary content of the file.
        """
        self.name: str = name
        self.size: int = size
        self.content: bytes = content

    def read(self) -> bytes:
        """Read the file content.

        Returns:
            The binary content of the file.
        """
        return self.content


def test_storage_logic() -> None:
    """Test the file storage logic and fallback mechanisms.

    This function tests the complete storage logic including:
    - File key generation from uploaded files
    - Directory fallback logic (when /data is not available)
    - File persistence and cleanup

    The test creates a mock uploaded file, generates a storage key,
    creates the storage directory (with fallback), writes a test file,
    verifies everything was created correctly, then cleans up.

    Raises:
        AssertionError: If any verification step fails.

    Example:
        >>> test_storage_logic()
        Testing storage logic...
        Using DATA_DIR: /path/to/data
        Successfully verified storage at /path/to/data/processed_...
    """
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
