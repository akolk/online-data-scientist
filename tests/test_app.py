"""Test suite for app.py helper functions.

This module tests the core helper functions in app.py that can be tested
without requiring full Streamlit context.
"""

import sys
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import polars as pl
import pytest


def clear_app_module():
    """Remove app module from cache to allow fresh imports with mocks."""
    modules_to_remove = [key for key in sys.modules.keys() if key == 'app' or key.startswith('app.')]
    for mod in modules_to_remove:
        del sys.modules[mod]


class TestGetFileKey:
    """Test cases for get_file_key function."""
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks before each test."""
        clear_app_module()
        
        # Create comprehensive mock for streamlit
        self.mock_st = MagicMock()
        self.mock_st.session_state = MagicMock()
        self.mock_st.session_state.__getitem__ = MagicMock()
        self.mock_st.session_state.__setitem__ = MagicMock()
        
        # Patch streamlit before importing app
        self.patcher = patch.dict('sys.modules', {
            'streamlit': self.mock_st,
            'streamlit_folium': MagicMock(),
            'geopandas': MagicMock(),
            'altair': MagicMock(),
            'plotly': MagicMock(),
            'plotly.express': MagicMock(),
            'plotly.graph_objects': MagicMock(),
            'folium': MagicMock(),
            'pydantic_ai': MagicMock(),
        })
        self.patcher.start()
        
        yield
        
        self.patcher.stop()
        clear_app_module()
    
    def test_returns_none_for_empty_files(self):
        """Test that get_file_key returns None when no files are provided."""
        from app import get_file_key
        
        result = get_file_key(None)
        assert result is None
        
        result = get_file_key([])
        assert result is None
    
    def test_generates_consistent_key_for_single_file(self):
        """Test that get_file_key generates consistent keys for the same file."""
        from app import get_file_key
        
        mock_file = Mock()
        mock_file.name = "test.csv"
        mock_file.size = 1024
        
        key1 = get_file_key([mock_file])
        key2 = get_file_key([mock_file])
        
        assert key1 == key2
        assert key1.startswith("processed_")
        # File name is sanitized (dots replaced with underscores)
        assert "test" in key1 and "csv" in key1
    
    def test_generates_consistent_key_for_multiple_files(self):
        """Test that get_file_key generates consistent keys regardless of file order."""
        from app import get_file_key
        
        mock_file1 = Mock()
        mock_file1.name = "a.csv"
        mock_file1.size = 100
        
        mock_file2 = Mock()
        mock_file2.name = "b.csv"
        mock_file2.size = 200
        
        # Keys should be the same regardless of order
        key1 = get_file_key([mock_file1, mock_file2])
        key2 = get_file_key([mock_file2, mock_file1])
        
        assert key1 == key2
    
    def test_sanitizes_special_characters(self):
        """Test that get_file_key sanitizes special characters in filenames."""
        from app import get_file_key
        
        mock_file = Mock()
        mock_file.name = "test-file@v1.0.csv"
        mock_file.size = 1024
        
        key = get_file_key([mock_file])
        
        # Key should not contain special characters
        assert "@" not in key
        assert key.startswith("processed_")
    
    def test_uses_hash_for_long_keys(self):
        """Test that get_file_key uses MD5 hash when key is too long (>200 chars)."""
        from app import get_file_key
        
        mock_file = Mock()
        mock_file.name = "a" * 250 + ".csv"  # Very long filename
        mock_file.size = 1024
        
        key = get_file_key([mock_file])
        
        # Should use hash (32 chars hex)
        assert len(key) <= 50  # processed_ + 32 char hash
        assert key.startswith("processed_")
    
    def test_includes_file_size_in_key(self):
        """Test that file size is included in the key generation."""
        from app import get_file_key
        
        mock_file1 = Mock()
        mock_file1.name = "test.csv"
        mock_file1.size = 1024
        
        mock_file2 = Mock()
        mock_file2.name = "test.csv"
        mock_file2.size = 2048
        
        key1 = get_file_key([mock_file1])
        key2 = get_file_key([mock_file2])
        
        assert key1 != key2


class TestDisplayResult:
    """Test cases for display_result function with pandas and polars DataFrames."""
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks before each test."""
        clear_app_module()
        
        # Create comprehensive mock for streamlit
        self.mock_st = MagicMock()
        
        # Create proper classes for isinstance checks
        class MockChart:
            pass
        
        class MockFigure:
            pass
        
        class MockMap:
            pass
        
        class MockFoliumFigure:
            pass
        
        class MockGeoDataFrame:
            pass
        
        mock_altair = MagicMock()
        mock_altair.Chart = MockChart
        
        mock_plotly_go = MagicMock()
        mock_plotly_go.Figure = MockFigure
        
        mock_folium = MagicMock()
        mock_folium.Map = MockMap
        mock_folium.Figure = MockFoliumFigure
        
        mock_gpd = MagicMock()
        mock_gpd.GeoDataFrame = MockGeoDataFrame
        
        # Patch streamlit before importing app
        self.patcher = patch.dict('sys.modules', {
            'streamlit': self.mock_st,
            'streamlit_folium': MagicMock(),
            'geopandas': mock_gpd,
            'altair': mock_altair,
            'plotly': MagicMock(),
            'plotly.express': MagicMock(),
            'plotly.graph_objects': mock_plotly_go,
            'folium': mock_folium,
            'pydantic_ai': MagicMock(),
        })
        self.patcher.start()
        
        yield
        
        self.patcher.stop()
        clear_app_module()
    
    def test_handles_pandas_dataframe(self):
        """Test that display_result correctly handles pandas DataFrames."""
        from app import display_result
        
        df = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        display_result(df)
        
        self.mock_st.dataframe.assert_called_once()
    
    def test_handles_polars_dataframe(self):
        """Test that display_result correctly handles polars DataFrames."""
        from app import display_result
        
        df = pl.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        display_result(df)
        
        self.mock_st.dataframe.assert_called_once()


class TestAnalysisResponseModel:
    """Test cases for AnalysisResponse Pydantic model validation."""
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks before each test."""
        clear_app_module()
        
        # Patch streamlit before importing app
        self.patcher = patch.dict('sys.modules', {
            'streamlit': MagicMock(),
            'streamlit_folium': MagicMock(),
            'geopandas': MagicMock(),
            'altair': MagicMock(),
            'plotly': MagicMock(),
            'plotly.express': MagicMock(),
            'plotly.graph_objects': MagicMock(),
            'folium': MagicMock(),
            'pydantic_ai': MagicMock(),
        })
        self.patcher.start()
        
        yield
        
        self.patcher.stop()
        clear_app_module()
    
    def test_model_creation_with_required_fields(self):
        """Test that AnalysisResponse can be created with required fields."""
        from app import AnalysisResponse
        
        response = AnalysisResponse(
            answer="Test answer",
            related=["Q1", "Q2"]
        )
        
        assert response.answer == "Test answer"
        assert response.related == ["Q1", "Q2"]
        assert response.code is None
        assert response.disclaimer is None
    
    def test_model_creation_with_all_fields(self):
        """Test that AnalysisResponse can be created with all fields."""
        from app import AnalysisResponse
        
        response = AnalysisResponse(
            answer="Test answer",
            related=["Q1", "Q2"],
            code="result = 42",
            disclaimer="Test disclaimer"
        )
        
        assert response.answer == "Test answer"
        assert response.code == "result = 42"
        assert response.disclaimer == "Test disclaimer"
    
    def test_model_related_max_length(self):
        """Test that related field enforces max_length constraint."""
        from app import AnalysisResponse
        
        # Should accept 2 items (max_length=2)
        response = AnalysisResponse(
            answer="Test",
            related=["Q1", "Q2"]
        )
        assert len(response.related) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
