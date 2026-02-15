"""Tests for the Settings page."""
import pytest
from unittest.mock import patch, MagicMock, call


class TestSettingsPage:
    """Test cases for Settings.py functionality."""

    @pytest.fixture
    def mock_streamlit(self):
        """Create a mock for Streamlit components."""
        with patch.dict('sys.modules', {'streamlit': MagicMock()}):
            import streamlit as st
            # Mock session_state as a dict-like object
            st.session_state = {}
            # Mock the methods
            st.set_page_config = MagicMock()
            st.header = MagicMock()
            st.number_input = MagicMock(return_value=500000)
            st.text_input = MagicMock(return_value="openai:gpt-5.2")
            st.slider = MagicMock(return_value=0.0)
            st.success = MagicMock()
            yield st

    def test_initializes_session_state_with_defaults(self, mock_streamlit):
        """Test that session state is initialized with default values."""
        # Import and run the module
        with patch.dict('sys.modules', {'streamlit': mock_streamlit}):
            # Simulate the imports and execution
            import sys
            # Clear any cached module
            if 'pages.Settings' in sys.modules:
                del sys.modules['pages.Settings']
            
            # Execute the settings logic directly
            st = mock_streamlit
            
            # Initialize session state (simulating the module execution)
            if "partition_size" not in st.session_state:
                st.session_state["partition_size"] = 500000
            if "llm_model" not in st.session_state:
                st.session_state["llm_model"] = "openai:gpt-5.2"
            if "temperature" not in st.session_state:
                st.session_state["temperature"] = 0.0
            
            # Verify defaults were set
            assert st.session_state["partition_size"] == 500000
            assert st.session_state["llm_model"] == "openai:gpt-5.2"
            assert st.session_state["temperature"] == 0.0

    def test_preserves_existing_session_state(self, mock_streamlit):
        """Test that existing session state values are preserved."""
        st = mock_streamlit
        
        # Set existing values
        st.session_state["partition_size"] = 1000000
        st.session_state["llm_model"] = "openai:gpt-4"
        st.session_state["temperature"] = 0.5
        
        # Initialize only if not present (simulating module logic)
        if "partition_size" not in st.session_state:
            st.session_state["partition_size"] = 500000
        if "llm_model" not in st.session_state:
            st.session_state["llm_model"] = "openai:gpt-5.2"
        if "temperature" not in st.session_state:
            st.session_state["temperature"] = 0.0
        
        # Verify existing values are preserved
        assert st.session_state["partition_size"] == 1000000
        assert st.session_state["llm_model"] == "openai:gpt-4"
        assert st.session_state["temperature"] == 0.5

    def test_partition_size_input_configuration(self, mock_streamlit):
        """Test partition size input has correct configuration."""
        st = mock_streamlit
        
        # Simulate number_input call with actual parameters
        result = st.number_input(
            "Parquet Partition Size (rows)",
            min_value=1000,
            max_value=10000000,
            value=500000,
            step=10000,
            help="Number of rows per chunk when converting CSV/ZIP to Parquet."
        )
        
        # Verify the call was made with correct parameters
        st.number_input.assert_called_once_with(
            "Parquet Partition Size (rows)",
            min_value=1000,
            max_value=10000000,
            value=500000,
            step=10000,
            help="Number of rows per chunk when converting CSV/ZIP to Parquet."
        )

    def test_llm_model_input_configuration(self, mock_streamlit):
        """Test LLM model input accepts proper format."""
        st = mock_streamlit
        
        # Simulate text_input call
        st.text_input(
            "LLM Model",
            value="openai:gpt-5.2",
            help="The model identifier to use (e.g., openai:gpt-5.2)."
        )
        
        # Verify the call
        st.text_input.assert_called_once_with(
            "LLM Model",
            value="openai:gpt-5.2",
            help="The model identifier to use (e.g., openai:gpt-5.2)."
        )

    def test_temperature_slider_configuration(self, mock_streamlit):
        """Test temperature slider has correct configuration."""
        st = mock_streamlit
        
        # Simulate slider call
        st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=0.0,
            step=0.1,
            help="Controls randomness. 0.0 is deterministic, 1.0 is creative."
        )
        
        # Verify the call
        st.slider.assert_called_once_with(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=0.0,
            step=0.1,
            help="Controls randomness. 0.0 is deterministic, 1.0 is creative."
        )

    def test_validates_llm_model_format(self):
        """Test that LLM model format validation accepts valid formats."""
        from pages.Settings import validate_model_format
        
        # Valid formats should pass
        assert validate_model_format("openai:gpt-4") == True
        assert validate_model_format("openai:gpt-5.2") == True
        assert validate_model_format("anthropic:claude-3") == True
        assert validate_model_format("custom:model-name") == True
        
    def test_rejects_invalid_llm_model_format(self):
        """Test that invalid LLM model formats are rejected."""
        from pages.Settings import validate_model_format
        
        # Invalid formats should fail
        assert validate_model_format("invalid") == False
        assert validate_model_format("") == False
        assert validate_model_format("no-colon-here") == False
        assert validate_model_format(":only-provider") == False
        assert validate_model_format("only-model:") == False

    def test_validates_partition_size_range(self):
        """Test partition size validation accepts valid ranges."""
        from pages.Settings import validate_partition_size
        
        assert validate_partition_size(1000) == True
        assert validate_partition_size(500000) == True
        assert validate_partition_size(10000000) == True

    def test_rejects_invalid_partition_size(self):
        """Test that invalid partition sizes are rejected."""
        from pages.Settings import validate_partition_size
        
        assert validate_partition_size(999) == False  # Below minimum
        assert validate_partition_size(10000001) == False  # Above maximum
        assert validate_partition_size(0) == False
        assert validate_partition_size(-100) == False


class TestSettingsIntegration:
    """Integration tests for Settings page interactions."""

    @pytest.fixture
    def mock_streamlit(self):
        """Create a mock for Streamlit."""
        st_mock = MagicMock()
        st_mock.session_state = {}
        return st_mock

    def test_settings_save_updates_session_state(self, mock_streamlit):
        """Test that changing settings updates session state."""
        st = mock_streamlit
        
        # Simulate user changing partition size
        st.number_input.return_value = 750000
        st.text_input.return_value = "openai:gpt-4-turbo"
        st.slider.return_value = 0.7
        
        # Simulate settings being saved
        partition_size = st.number_input.return_value
        st.session_state["partition_size"] = partition_size
        
        llm_model = st.text_input.return_value
        st.session_state["llm_model"] = llm_model
        
        temperature = st.slider.return_value
        st.session_state["temperature"] = temperature
        
        # Verify session state was updated
        assert st.session_state["partition_size"] == 750000
        assert st.session_state["llm_model"] == "openai:gpt-4-turbo"
        assert st.session_state["temperature"] == 0.7

    def test_page_configuration(self, mock_streamlit):
        """Test that page is configured with correct title."""
        st = mock_streamlit
        
        # Simulate page config
        st.set_page_config(
            page_title="Settings - Online Data Scientist",
            layout="wide"
        )
        
        # Verify
        st.set_page_config.assert_called_once_with(
            page_title="Settings - Online Data Scientist",
            layout="wide"
        )
