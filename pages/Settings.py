"""Settings page for the Online Data Scientist application.

This module provides the settings interface for configuring application
parameters including partition size, LLM model selection, and temperature.
Settings are persisted in Streamlit's session state.

Usage:
    This module is automatically loaded by Streamlit when users navigate
    to the Settings page via the sidebar. It reads and writes to
    st.session_state to maintain configuration across page reloads.
"""

import logging
import re

import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Settings - Online Data Scientist", layout="wide")

st.header("Settings")


def validate_model_format(model: str) -> bool:
    """
    Validate LLM model format (e.g., 'provider:model-name').

    Args:
        model: The model identifier string to validate

    Returns:
        True if format is valid, False otherwise
    """
    if not model or not isinstance(model, str):
        logger.debug(f"Model validation failed: invalid type or empty value")
        return False

    # Pattern: provider:model-name
    # Both provider and model-name must be non-empty
    pattern = r'^[a-zA-Z0-9_-]+:[a-zA-Z0-9_.-]+$'
    is_valid = bool(re.match(pattern, model))

    if not is_valid:
        logger.warning(f"Invalid LLM model format: '{model}'. Expected format: 'provider:model-name'")
    else:
        logger.debug(f"Model format validated successfully: '{model}'")

    return is_valid


def validate_partition_size(size: int) -> bool:
    """
    Validate partition size is within acceptable range.

    Args:
        size: The partition size in rows

    Returns:
        True if size is valid, False otherwise
    """
    if not isinstance(size, (int, float)):
        logger.debug(f"Partition size validation failed: invalid type {type(size)}")
        return False

    min_size = 1000
    max_size = 10000000

    is_valid = min_size <= size <= max_size

    if not is_valid:
        logger.warning(
            f"Invalid partition size: {size}. Must be between {min_size} and {max_size}"
        )
    else:
        logger.debug(f"Partition size validated successfully: {size}")

    return is_valid


# Initialize session state if not present (although app.py usually runs first, direct navigation is possible)
if "partition_size" not in st.session_state:
    st.session_state.partition_size = 500000
    logger.debug(f"Initialized partition_size to default: {st.session_state.partition_size}")
if "llm_model" not in st.session_state:
    st.session_state.llm_model = "openai:gpt-5.2"
    logger.debug(f"Initialized llm_model to default: {st.session_state.llm_model}")
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.0
    logger.debug(f"Initialized temperature to default: {st.session_state.temperature}")

# Partition Size
partition_size = st.number_input(
    "Parquet Partition Size (rows)",
    min_value=1000,
    max_value=10000000,
    value=st.session_state.partition_size,
    step=10000,
    help="Number of rows per chunk when converting CSV/ZIP to Parquet."
)
st.session_state.partition_size = partition_size

# LLM Model
llm_model = st.text_input(
    "LLM Model",
    value=st.session_state.llm_model,
    help="The model identifier to use (e.g., openai:gpt-5.2)."
)
st.session_state.llm_model = llm_model

# Temperature
temperature = st.slider(
    "Temperature",
    min_value=0.0,
    max_value=2.0,
    value=st.session_state.temperature,
    step=0.1,
    help="Controls randomness. 0.0 is deterministic, 1.0 is creative."
)
st.session_state.temperature = temperature

# Log settings updates for debugging
logger.debug(
    f"Settings updated - partition_size: {partition_size}, "
    f"llm_model: {llm_model}, temperature: {temperature}"
)

st.success("Settings saved automatically.")
