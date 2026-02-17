"""Settings storage module for persistent configuration.

This module provides functionality to save and load application settings
from a JSON file, allowing user preferences to persist across sessions.

Settings are stored in a JSON file located at ~/.config/online-data-scientist/settings.json
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Default settings values
DEFAULT_SETTINGS = {
    "partition_size": 500000,
    "llm_model": "openai:gpt-5.2",
    "temperature": 0.0,
}

# Settings file location
SETTINGS_DIR = Path.home() / ".config" / "online-data-scientist"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


def get_settings_path() -> Path:
    """
    Get the path to the settings file.

    Returns:
        Path object pointing to the settings JSON file.
    """
    return SETTINGS_FILE


def ensure_settings_directory() -> bool:
    """
    Ensure the settings directory exists.

    Returns:
        True if directory exists or was created successfully, False otherwise.
    """
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Settings directory ensured: {SETTINGS_DIR}")
        return True
    except (OSError, IOError) as e:
        logger.error(f"Failed to create settings directory: {e}")
        return False


def load_settings() -> Dict[str, Any]:
    """
    Load settings from the JSON file.

    Returns a dictionary containing the saved settings, or default values
    if the file doesn't exist or is invalid.

    Returns:
        Dictionary with setting names as keys and their values.
    """
    if not SETTINGS_FILE.exists():
        logger.debug(f"Settings file not found, using defaults: {DEFAULT_SETTINGS}")
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            saved_settings = json.load(f)

        # Merge with defaults to ensure all keys exist
        settings = DEFAULT_SETTINGS.copy()
        settings.update(saved_settings)

        logger.debug(f"Settings loaded successfully: {settings}")
        return settings

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in settings file: {e}. Using defaults.")
        return DEFAULT_SETTINGS.copy()
    except (OSError, IOError) as e:
        logger.error(f"Failed to read settings file: {e}. Using defaults.")
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> bool:
    """
    Save settings to the JSON file.

    Args:
        settings: Dictionary containing settings to save.

    Returns:
        True if settings were saved successfully, False otherwise.
    """
    # Ensure directory exists
    if not ensure_settings_directory():
        return False

    try:
        # Filter to only save known settings
        valid_settings = {
            key: value for key, value in settings.items()
            if key in DEFAULT_SETTINGS
        }

        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(valid_settings, f, indent=2)

        logger.debug(f"Settings saved successfully: {valid_settings}")
        return True

    except (OSError, IOError, TypeError) as e:
        logger.error(f"Failed to save settings: {e}")
        return False


def get_setting(key: str, default: Any = None) -> Any:
    """
    Get a specific setting value.

    Args:
        key: The setting name to retrieve.
        default: Default value if setting doesn't exist.

    Returns:
        The setting value or the default.
    """
    settings = load_settings()
    return settings.get(key, default)


def update_setting(key: str, value: Any) -> bool:
    """
    Update a single setting value.

    Args:
        key: The setting name to update.
        value: The new value for the setting.

    Returns:
        True if setting was updated successfully, False otherwise.
    """
    settings = load_settings()
    settings[key] = value
    return save_settings(settings)


def reset_to_defaults() -> bool:
    """
    Reset all settings to their default values.

    Returns:
        True if settings were reset successfully, False otherwise.
    """
    logger.info("Resetting settings to defaults")
    return save_settings(DEFAULT_SETTINGS)


def migrate_legacy_settings() -> bool:
    """
    Migrate settings from legacy locations if present.

    Checks for settings in old locations and migrates them to the new
    standard location.

    Returns:
        True if migration was performed, False otherwise.
    """
    # Legacy location: settings in working directory
    legacy_file = Path("settings.json")

    if legacy_file.exists() and not SETTINGS_FILE.exists():
        try:
            with open(legacy_file, 'r', encoding='utf-8') as f:
                legacy_settings = json.load(f)

            logger.info(f"Migrating legacy settings from {legacy_file}")
            return save_settings(legacy_settings)

        except (json.JSONDecodeError, OSError, IOError) as e:
            logger.warning(f"Failed to migrate legacy settings: {e}")
            return False

    return False
