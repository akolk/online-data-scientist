"""Validation utilities for the Online Data Scientist application.

This module provides validation functions for user inputs and configuration
settings. These functions are independent of Streamlit and can be used
throughout the application.

Functions:
    validate_model_format: Validates LLM model identifier format
    validate_partition_size: Validates partition size is within acceptable range
"""

import logging
import re

# Configure logging
logger = logging.getLogger(__name__)


def validate_model_format(model: str) -> bool:
    """
    Validate LLM model format (e.g., 'provider:model-name').

    Args:
        model: The model identifier string to validate

    Returns:
        True if format is valid, False otherwise

    Examples:
        >>> validate_model_format("openai:gpt-4")
        True
        >>> validate_model_format("invalid")
        False
    """
    if not model or not isinstance(model, str):
        logger.debug("Model validation failed: invalid type or empty value")
        return False

    # Pattern: provider:model-name
    # Both provider and model-name must be non-empty
    # Provider can contain alphanumeric, underscore, and hyphen
    # Model name can contain alphanumeric, underscore, hyphen, and dot
    pattern = r'^[a-zA-Z0-9_-]+:[a-zA-Z0-9_.-]+$'
    is_valid = bool(re.match(pattern, model))

    if not is_valid:
        logger.warning(
            f"Invalid LLM model format: '{model}'. "
            f"Expected format: 'provider:model-name'"
        )
    else:
        logger.debug(f"Model format validated successfully: '{model}'")

    return is_valid


def validate_partition_size(size) -> bool:
    """
    Validate partition size is within acceptable range.

    Args:
        size: The partition size in rows (int or float)

    Returns:
        True if size is valid, False otherwise

    Examples:
        >>> validate_partition_size(500000)
        True
        >>> validate_partition_size(999)
        False
    """
    if not isinstance(size, (int, float)):
        logger.debug(f"Partition size validation failed: invalid type {type(size)}")
        return False

    min_size = 1000
    max_size = 10000000

    is_valid = min_size <= size <= max_size

    if not is_valid:
        logger.warning(
            f"Invalid partition size: {size}. "
            f"Must be between {min_size} and {max_size}"
        )
    else:
        logger.debug(f"Partition size validated successfully: {size}")

    return is_valid
