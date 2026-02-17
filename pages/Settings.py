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

import streamlit as st

from validators import validate_model_format, validate_partition_size

# Configure logging
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Settings - Online Data Scientist", layout="wide")

st.header("Settings")


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
if validate_partition_size(partition_size):
    st.session_state.partition_size = partition_size
else:
    st.error(f"Partition size must be between 1000 and 10000000 rows.")

# LLM Model
llm_model = st.text_input(
    "LLM Model",
    value=st.session_state.llm_model,
    help="The model identifier to use (e.g., openai:gpt-5.2)."
)
if validate_model_format(llm_model):
    st.session_state.llm_model = llm_model
else:
    st.error("Model format should be 'provider:model-name' (e.g., 'openai:gpt-5.2').")

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
