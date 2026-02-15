import streamlit as st
import re

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
        return False
    
    # Pattern: provider:model-name
    # Both provider and model-name must be non-empty
    pattern = r'^[a-zA-Z0-9_-]+:[a-zA-Z0-9_.-]+$'
    return bool(re.match(pattern, model))


def validate_partition_size(size: int) -> bool:
    """
    Validate partition size is within acceptable range.
    
    Args:
        size: The partition size in rows
        
    Returns:
        True if size is valid, False otherwise
    """
    if not isinstance(size, (int, float)):
        return False
    
    min_size = 1000
    max_size = 10000000
    
    return min_size <= size <= max_size

# Initialize session state if not present (although app.py usually runs first, direct navigation is possible)
if "partition_size" not in st.session_state:
    st.session_state.partition_size = 500000
if "llm_model" not in st.session_state:
    st.session_state.llm_model = "openai:gpt-5.2"
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.0

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

st.success("Settings saved automatically.")
