
import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Mock streamlit
mock_st = MagicMock()
sys.modules["streamlit"] = mock_st
sys.modules["streamlit.components"] = MagicMock()
sys.modules["streamlit.components.v1"] = MagicMock()

# Configure st.columns to return 2 mocks
mock_st.columns.return_value = (MagicMock(), MagicMock())
# Configure st.sidebar to be a context manager
mock_st.sidebar.__enter__.return_value = MagicMock()
mock_st.sidebar.__exit__.return_value = None

# Set env var to avoid st.stop()
os.environ["OPENAI_API_KEY"] = "fake-key"
os.environ["MCP_ENDPOINT"] = "http://fake"

# We need to mock openai.OpenAI before importing app because it initializes client at module level
with patch("openai.OpenAI") as MockOpenAI:
    # Setup the mock client instance
    mock_client = MagicMock()
    MockOpenAI.return_value = mock_client

    # Setup the response structure
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello there!"
    mock_client.chat.completions.create.return_value = mock_response

    # Import app
    import app

class TestAppOpenAIMigration(unittest.TestCase):
    def test_call_openai_chat(self):
        # Reset the mock to ignore calls made during import/setup if any
        app.client.chat.completions.create.reset_mock()

        # Arrange
        messages = [{"role": "user", "content": "Hi"}]

        # Act
        response_content = app.call_openai_chat(messages)

        # Assert
        # Check if the response is what we expect
        self.assertIsInstance(response_content, tuple)
        self.assertEqual(response_content[0], "Hello there!")

        # Verify that the new API method was called
        app.client.chat.completions.create.assert_called_once()

        # Verify arguments
        call_args = app.client.chat.completions.create.call_args
        self.assertEqual(call_args.kwargs["messages"], messages)
        self.assertEqual(call_args.kwargs["model"], "gpt-4o-mini")

if __name__ == "__main__":
    unittest.main()
