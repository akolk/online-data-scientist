"""Test suite for settings_storage.py module.

This module provides comprehensive test coverage for the settings storage
functionality, including loading, saving, and managing persistent settings.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

import pytest

# Import after clearing cache to ensure fresh import
def clear_settings_module():
    """Remove settings_storage module from cache to allow fresh imports."""
    modules_to_remove = [key for key in sys.modules.keys()
                         if key == 'settings_storage' or key.startswith('settings_storage.')]
    for mod in modules_to_remove:
        del sys.modules[mod]


class TestGetSettingsPath:
    """Test cases for get_settings_path function."""

    def test_returns_path_object(self):
        """Test that get_settings_path returns a Path object."""
        from settings_storage import get_settings_path
        result = get_settings_path()
        assert isinstance(result, Path)

    def test_returns_correct_path_structure(self):
        """Test that the returned path has the expected structure."""
        from settings_storage import get_settings_path
        result = get_settings_path()
        assert result.name == "settings.json"
        assert ".config" in str(result)
        assert "online-data-scientist" in str(result)

    def test_returns_consistent_path(self):
        """Test that multiple calls return the same path."""
        from settings_storage import get_settings_path
        path1 = get_settings_path()
        path2 = get_settings_path()
        assert path1 == path2


class TestEnsureSettingsDirectory:
    """Test cases for ensure_settings_directory function."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Setup test environment with temporary directory."""
        self.temp_dir = tmp_path
        self.settings_dir = tmp_path / ".config" / "online-data-scientist"
        yield

    def test_creates_directory_when_not_exists(self):
        """Test that directory is created when it doesn't exist."""
        from settings_storage import ensure_settings_directory, SETTINGS_DIR

        mock_path = MagicMock()
        with patch('settings_storage.SETTINGS_DIR', mock_path):
            mock_path.mkdir.return_value = None
            result = ensure_settings_directory()
            assert result is True
            mock_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_returns_true_when_directory_exists(self):
        """Test that function returns True when directory already exists."""
        from settings_storage import ensure_settings_directory, SETTINGS_DIR

        mock_path = MagicMock()
        with patch('settings_storage.SETTINGS_DIR', mock_path):
            mock_path.mkdir.return_value = None
            result = ensure_settings_directory()
            assert result is True

    def test_returns_false_on_permission_error(self):
        """Test that function returns False when permission is denied."""
        from settings_storage import ensure_settings_directory, SETTINGS_DIR

        mock_path = MagicMock()
        with patch('settings_storage.SETTINGS_DIR', mock_path):
            mock_path.mkdir.side_effect = PermissionError("Permission denied")
            result = ensure_settings_directory()
            assert result is False


class TestLoadSettings:
    """Test cases for load_settings function."""

    def test_returns_defaults_when_file_not_exists(self):
        """Test that defaults are returned when settings file doesn't exist."""
        from settings_storage import load_settings, DEFAULT_SETTINGS

        mock_path = MagicMock()
        mock_path.exists.return_value = False

        with patch('settings_storage.SETTINGS_FILE', mock_path):
            result = load_settings()
            assert result == DEFAULT_SETTINGS

    def test_loads_settings_from_file(self):
        """Test that settings are loaded from existing file."""
        from settings_storage import load_settings

        mock_settings = {
            "partition_size": 100000,
            "llm_model": "anthropic:claude-3",
            "temperature": 0.5
        }

        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with patch('settings_storage.SETTINGS_FILE', mock_path):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):
                result = load_settings()
                assert result["partition_size"] == 100000
                assert result["llm_model"] == "anthropic:claude-3"
                assert result["temperature"] == 0.5

    def test_merges_with_defaults(self):
        """Test that saved settings are merged with defaults."""
        from settings_storage import load_settings, DEFAULT_SETTINGS

        mock_settings = {
            "partition_size": 100000
            # Missing llm_model and temperature
        }

        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with patch('settings_storage.SETTINGS_FILE', mock_path):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):
                result = load_settings()
                # Should have the saved value
                assert result["partition_size"] == 100000
                # Should have defaults for missing keys
                assert result["llm_model"] == DEFAULT_SETTINGS["llm_model"]
                assert result["temperature"] == DEFAULT_SETTINGS["temperature"]

    def test_returns_defaults_on_invalid_json(self):
        """Test that defaults are returned when file contains invalid JSON."""
        from settings_storage import load_settings, DEFAULT_SETTINGS

        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with patch('settings_storage.SETTINGS_FILE', mock_path):
            with patch('builtins.open', mock_open(read_data="invalid json")):
                with patch('json.load', side_effect=json.JSONDecodeError("test", "", 0)):
                    result = load_settings()
                    assert result == DEFAULT_SETTINGS

    def test_returns_defaults_on_read_error(self):
        """Test that defaults are returned when file cannot be read."""
        from settings_storage import load_settings, DEFAULT_SETTINGS

        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with patch('settings_storage.SETTINGS_FILE', mock_path):
            with patch('builtins.open', side_effect=IOError("Cannot read file")):
                result = load_settings()
                assert result == DEFAULT_SETTINGS


class TestSaveSettings:
    """Test cases for save_settings function."""

    def test_saves_valid_settings(self, tmp_path):
        """Test that valid settings are saved to file."""
        from settings_storage import save_settings, ensure_settings_directory

        settings = {
            "partition_size": 100000,
            "llm_model": "openai:gpt-4",
            "temperature": 0.5
        }

        with patch('settings_storage.ensure_settings_directory', return_value=True):
            with patch('builtins.open', mock_open()) as mock_file:
                result = save_settings(settings)
                assert result is True
                mock_file.assert_called_once()

    def test_filters_unknown_settings(self):
        """Test that unknown settings are filtered out."""
        from settings_storage import save_settings, DEFAULT_SETTINGS

        settings = {
            "partition_size": 100000,
            "unknown_setting": "should_be_filtered",
            "another_unknown": 123
        }

        with patch('settings_storage.ensure_settings_directory', return_value=True):
            with patch('builtins.open', mock_open()) as mock_file:
                result = save_settings(settings)
                assert result is True

                # Check what was written
                handle = mock_file()
                written_data = ''.join(call.args[0] for call in handle.write.call_args_list)
                saved = json.loads(written_data)

                # Should only have known settings
                assert "partition_size" in saved
                assert "unknown_setting" not in saved
                assert "another_unknown" not in saved

    def test_returns_false_when_directory_creation_fails(self):
        """Test that function returns False when directory cannot be created."""
        from settings_storage import save_settings

        settings = {"partition_size": 100000}

        with patch('settings_storage.ensure_settings_directory', return_value=False):
            result = save_settings(settings)
            assert result is False

    def test_returns_false_on_write_error(self):
        """Test that function returns False when file cannot be written."""
        from settings_storage import save_settings

        settings = {"partition_size": 100000}

        with patch('settings_storage.ensure_settings_directory', return_value=True):
            with patch('builtins.open', side_effect=IOError("Cannot write")):
                result = save_settings(settings)
                assert result is False


class TestGetSetting:
    """Test cases for get_setting function."""

    def test_returns_existing_setting(self):
        """Test that existing setting is returned."""
        from settings_storage import get_setting

        mock_settings = {"partition_size": 100000, "temperature": 0.5}

        with patch('settings_storage.load_settings', return_value=mock_settings):
            result = get_setting("partition_size")
            assert result == 100000

    def test_returns_default_for_missing_setting(self):
        """Test that default is returned when setting doesn't exist."""
        from settings_storage import get_setting

        mock_settings = {"partition_size": 100000}

        with patch('settings_storage.load_settings', return_value=mock_settings):
            result = get_setting("nonexistent", default="default_value")
            assert result == "default_value"

    def test_returns_none_for_missing_setting_no_default(self):
        """Test that None is returned when setting doesn't exist and no default provided."""
        from settings_storage import get_setting

        mock_settings = {"partition_size": 100000}

        with patch('settings_storage.load_settings', return_value=mock_settings):
            result = get_setting("nonexistent")
            assert result is None


class TestUpdateSetting:
    """Test cases for update_setting function."""

    def test_updates_single_setting(self):
        """Test that a single setting is updated."""
        from settings_storage import update_setting

        mock_settings = {"partition_size": 500000, "temperature": 0.0}

        with patch('settings_storage.load_settings', return_value=mock_settings.copy()):
            with patch('settings_storage.save_settings', return_value=True) as mock_save:
                result = update_setting("partition_size", 100000)
                assert result is True

                # Check what was saved
                saved_args = mock_save.call_args[0][0]
                assert saved_args["partition_size"] == 100000

    def test_preserves_other_settings(self):
        """Test that updating one setting preserves others."""
        from settings_storage import update_setting

        mock_settings = {"partition_size": 500000, "temperature": 0.5, "llm_model": "test"}

        with patch('settings_storage.load_settings', return_value=mock_settings.copy()):
            with patch('settings_storage.save_settings', return_value=True) as mock_save:
                update_setting("partition_size", 100000)

                saved_args = mock_save.call_args[0][0]
                assert saved_args["temperature"] == 0.5
                assert saved_args["llm_model"] == "test"


class TestResetToDefaults:
    """Test cases for reset_to_defaults function."""

    def test_resets_all_settings(self):
        """Test that all settings are reset to defaults."""
        from settings_storage import reset_to_defaults, DEFAULT_SETTINGS

        with patch('settings_storage.save_settings') as mock_save:
            mock_save.return_value = True
            result = reset_to_defaults()
            assert result is True

            # Check that defaults were saved
            saved_args = mock_save.call_args[0][0]
            assert saved_args == DEFAULT_SETTINGS

    def test_returns_false_on_save_failure(self):
        """Test that function returns False when save fails."""
        from settings_storage import reset_to_defaults

        with patch('settings_storage.save_settings', return_value=False):
            result = reset_to_defaults()
            assert result is False


class TestMigrateLegacySettings:
    """Test cases for migrate_legacy_settings function."""

    def test_migrates_when_legacy_exists_and_new_doesnt(self):
        """Test migration when legacy file exists but new doesn't."""
        from settings_storage import migrate_legacy_settings

        legacy_settings = {"partition_size": 100000}

        # Mock the new settings file to not exist
        mock_new_file = MagicMock()
        mock_new_file.exists.return_value = False

        # Mock the legacy file to exist
        mock_legacy_path = MagicMock()
        mock_legacy_path.exists.return_value = True
        mock_legacy_path.__truediv__ = MagicMock(return_value=mock_legacy_path)
        mock_legacy_path.__rtruediv__ = MagicMock(return_value=mock_legacy_path)

        with patch('settings_storage.SETTINGS_FILE', mock_new_file):
            with patch('settings_storage.Path', return_value=mock_legacy_path):
                with patch('builtins.open', mock_open(read_data=json.dumps(legacy_settings))):
                    with patch('settings_storage.save_settings', return_value=True) as mock_save:
                        result = migrate_legacy_settings()
                        assert result is True
                        mock_save.assert_called_once_with(legacy_settings)

    def test_does_not_migrate_when_new_exists(self):
        """Test that migration is skipped when new file already exists."""
        from settings_storage import migrate_legacy_settings

        # Mock the new settings file to exist
        mock_new_file = MagicMock()
        mock_new_file.exists.return_value = True

        with patch('settings_storage.SETTINGS_FILE', mock_new_file):
            result = migrate_legacy_settings()
            assert result is False

    def test_does_not_migrate_when_no_legacy(self):
        """Test that migration is skipped when no legacy file exists."""
        from settings_storage import migrate_legacy_settings

        # Mock the new settings file to not exist
        mock_new_file = MagicMock()
        mock_new_file.exists.return_value = False

        # Mock the legacy file to not exist
        mock_legacy_path = MagicMock()
        mock_legacy_path.exists.return_value = False
        mock_legacy_path.__truediv__ = MagicMock(return_value=mock_legacy_path)
        mock_legacy_path.__rtruediv__ = MagicMock(return_value=mock_legacy_path)

        with patch('settings_storage.SETTINGS_FILE', mock_new_file):
            with patch('settings_storage.Path', return_value=mock_legacy_path):
                result = migrate_legacy_settings()
                assert result is False


class TestIntegration:
    """Integration tests for settings storage functionality."""

    def test_full_save_and_load_cycle(self, tmp_path):
        """Test that settings can be saved and loaded correctly."""
        from settings_storage import save_settings, load_settings, SETTINGS_FILE, SETTINGS_DIR

        # Use temporary directory
        test_settings_dir = tmp_path / ".config" / "test-app"
        test_settings_file = test_settings_dir / "settings.json"

        with patch('settings_storage.SETTINGS_DIR', test_settings_dir):
            with patch('settings_storage.SETTINGS_FILE', test_settings_file):
                settings = {
                    "partition_size": 750000,
                    "llm_model": "openai:gpt-4-turbo",
                    "temperature": 0.7
                }

                # Save settings
                save_result = save_settings(settings)
                assert save_result is True

                # Load settings back
                loaded = load_settings()
                assert loaded["partition_size"] == 750000
                assert loaded["llm_model"] == "openai:gpt-4-turbo"
                assert loaded["temperature"] == 0.7

    def test_settings_persist_across_operations(self, tmp_path):
        """Test that settings persist across multiple save/load operations."""
        from settings_storage import update_setting, get_setting
        from settings_storage import SETTINGS_DIR, SETTINGS_FILE

        test_settings_dir = tmp_path / ".config" / "test-app"
        test_settings_file = test_settings_dir / "settings.json"

        with patch('settings_storage.SETTINGS_DIR', test_settings_dir):
            with patch('settings_storage.SETTINGS_FILE', test_settings_file):
                # Update a setting
                update_setting("temperature", 1.0)

                # Get it back
                result = get_setting("temperature")
                assert result == 1.0


class TestDefaultSettings:
    """Test cases for DEFAULT_SETTINGS constant."""

    def test_contains_all_required_keys(self):
        """Test that DEFAULT_SETTINGS contains all required keys."""
        from settings_storage import DEFAULT_SETTINGS

        required_keys = ["partition_size", "llm_model", "temperature"]
        for key in required_keys:
            assert key in DEFAULT_SETTINGS

    def test_has_valid_default_values(self):
        """Test that default values are valid."""
        from settings_storage import DEFAULT_SETTINGS

        assert isinstance(DEFAULT_SETTINGS["partition_size"], int)
        assert DEFAULT_SETTINGS["partition_size"] > 0

        assert isinstance(DEFAULT_SETTINGS["llm_model"], str)
        assert ":" in DEFAULT_SETTINGS["llm_model"]

        assert isinstance(DEFAULT_SETTINGS["temperature"], (int, float))
        assert 0.0 <= DEFAULT_SETTINGS["temperature"] <= 2.0
