import os
import json
import re
import sys
import io
import hashlib
import logging
from typing import List, Optional, Any, Dict, Union
import streamlit as st
import pandas as pd
import geopandas as gpd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import polars as pl
import tempfile
import shutil
import copy
import data_processor
import code_executor
from pydantic import BaseModel, Field
from pydantic_ai import Agent

# Configure logging
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# 1️⃣  Configuration – read secrets from environment
# ----------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("❌ `OPENAI_API_KEY` is missing. Please set it in your environment.")
    st.stop()

class AnalysisResponse(BaseModel):
    answer: str = Field(
        ...,
        description="Short description of the results or why the request cannot be fulfilled."
    )
    related: List[str] = Field(
        ...,
        max_length=2,
        description="2 SHORT related follow-up USER question suggestions a USER may ask."
    )
    code: Optional[str] = Field(
        default=None,
        description="Complete, runnable Python script (no backticks) that assigns the final output to `result`."
    )
    disclaimer: Optional[str] = Field(
        default=None,
        description="Short disclaimer about data quality, limitations if applicable and urls of datasets used."
    )

# ----------------------------------------------------------------------
# 2️⃣  Helper functions
# ----------------------------------------------------------------------

def get_file_key(files: Optional[List[Any]]) -> Optional[str]:
    """Generates a consistent, safe key for a list of uploaded files."""
    if not files:
        return None
    sorted_files = sorted(files, key=lambda f: f.name)
    raw_key = "_".join([f"{f.name}_{f.size}" for f in sorted_files])
    # Sanitize to be safe for filesystem
    safe_key = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_key)
    if len(safe_key) > 200:
        safe_key = hashlib.md5(raw_key.encode()).hexdigest()
    return f"processed_{safe_key}"

def display_result(result: Any) -> None:
    """
    Render the result in the right column.
    Handles DataFrames, Charts, Maps, and text.
    """
    logger.debug(f"Result type: {type(result)}")
    logger.debug(f"Result value: {result}")
    if isinstance(result, (pd.DataFrame, pl.DataFrame)):
        st.dataframe(result)
    elif isinstance(result, (alt.Chart,)):
        st.altair_chart(result, width="stretch")
    elif isinstance(result, go.Figure):
        st.plotly_chart(result, width="stretch")
    elif isinstance(result, (folium.Map, folium.Figure)):
         st_folium(result, width=700)
    elif isinstance(result, gpd.GeoDataFrame):
        # Simple folium map – show centroids
        if not result.empty and result.geometry.notnull().any():
             m = folium.Map(location=[result.geometry.y.mean(), result.geometry.x.mean()],
                            zoom_start=5)
             for _, row in result.iterrows():
                 if row.geometry:
                     folium.GeoJson(row.geometry).add_to(m)
             st_folium(m, width=700)
        st.dataframe(result)
    else:
        st.write(result)

def settings_page() -> None:
    st.header("Settings")

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


# ----------------------------------------------------------------------
# 3️⃣  Streamlit UI
# ----------------------------------------------------------------------
st.set_page_config(page_title="🧠 Online Data Scientist", layout="wide")

# Top Menu Bar
page = st.radio("Menu", ["Home", "Settings"], horizontal=True, label_visibility="collapsed")

# Session state initialization
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "last_run_result" not in st.session_state:
    st.session_state.last_run_result = None

if "partition_size" not in st.session_state:
    st.session_state.partition_size = 500000

if "llm_model" not in st.session_state:
    st.session_state.llm_model = "openai:gpt-5.2"

if "temperature" not in st.session_state:
    st.session_state.temperature = 0.0

def home_page() -> None:
    # Progress bar container in the header
    progress_bar_placeholder = st.empty()

    # Sidebar for file upload
    with st.sidebar:
        st.header("Upload Data")
        uploaded_files = st.file_uploader("Choose CSV, ZIP or GZIP files", type=["csv", "zip", "gz", "gzip"], accept_multiple_files=True)

    if uploaded_files:
        # Check if already processed to avoid re-processing on every rerun
        # We use a composite key based on all files.
        sorted_files = sorted(uploaded_files, key=lambda f: f.name)
        file_key = get_file_key(uploaded_files)

        # Determine persistent storage location
        DATA_DIR = "/data"
        if not os.path.exists(DATA_DIR) or not os.access(DATA_DIR, os.W_OK):
            DATA_DIR = os.path.join(os.getcwd(), "data")
            os.makedirs(DATA_DIR, exist_ok=True)

        file_dir = os.path.join(DATA_DIR, file_key)

        # Check if files already exist in persistent storage
        existing_parquet = []
        if os.path.exists(file_dir) and os.path.isdir(file_dir):
            existing_parquet = [os.path.join(file_dir, f) for f in os.listdir(file_dir) if f.endswith('.parquet')]

        if existing_parquet and file_key not in st.session_state:
            st.session_state[file_key] = existing_parquet
            dataset_info = data_processor.get_dataset_info(existing_parquet)
            st.session_state[f"{file_key}_info"] = dataset_info
            st.success(f"Loaded {len(existing_parquet)} parquet files from storage.")

        elif file_key not in st.session_state:
            st.info("Processing files...")

            # Progress bar logic
            progress_bar = progress_bar_placeholder.progress(0, text="Starting extraction...")

            total_files = len(sorted_files)

            def make_progress_callback(file_index):
                def update_progress(p):
                    # p is 0.0 to 1.0 for the current file
                    # Global progress = (file_index + p) / total_files
                    global_p = (file_index + p) / total_files
                    progress_bar.progress(int(global_p * 100), text=f"Processing file {file_index+1}/{total_files}... {int(global_p*100)}%")
                return update_progress

            # Create/Use the persistent directory
            temp_dir = file_dir
            # If it exists but we are here, it means no parquet files were found or partial state. Clean up.
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)

            try:
                all_parquet_files = []
                for i, file_obj in enumerate(sorted_files):
                    # Process
                    parquet_files = data_processor.extract_and_convert(
                        file_obj,
                        file_obj.name,
                        temp_dir,
                        make_progress_callback(i),
                        chunk_size=st.session_state.partition_size
                    )
                    all_parquet_files.extend(parquet_files)

                if not all_parquet_files:
                    st.error("No valid data could be extracted from the uploaded files.")
                    # Clean up since we failed to get data
                    shutil.rmtree(temp_dir, ignore_errors=True)
                else:
                    st.session_state[file_key] = all_parquet_files
                    # Extract metadata
                    dataset_info = data_processor.get_dataset_info(all_parquet_files)
                    st.session_state[f"{file_key}_info"] = dataset_info
                    st.success(f"Processed {len(all_parquet_files)} parquet files.")

                # Clear progress bar
                progress_bar.empty()

            except Exception as e:
                st.error(f"Error processing files: {e}")
                progress_bar.empty()
                # Clean up on failure
                shutil.rmtree(temp_dir, ignore_errors=True)

        # If processed, load it into analysis result
        if file_key in st.session_state:
            parquet_files = st.session_state[file_key]

            # Calculate total size of parquet files
            total_size_bytes = sum(os.path.getsize(f) for f in parquet_files)
            total_size_mb = total_size_bytes / (1024 * 1024)

            st.write(f"Partitions: {len(parquet_files)} | Total Size: {total_size_mb:.2f} MB")

            if parquet_files and st.button("Load Uploaded Data into Analysis"):
                # Use LazyFrame to load
                try:
                    # Scan all parquet files
                    lf = pl.scan_parquet(parquet_files)

                    # For rendering, we might need to collect a sample or use a specialized renderer.
                    # The current render_analysis expects pandas/geopandas.
                    # We'll collect the head.
                    df_pandas = lf.limit(1000).collect().to_pandas()

                    st.session_state.last_run_result = df_pandas
                    st.success("Data loaded into Analysis view.")
                except Exception as e:
                    st.error(f"Failed to load data: {e}")


    # Two‑column layout: chat | analysis
    col_chat, col_analysis = st.columns([4, 6])

    # ---- Chat panel ----
    with col_chat:
        st.header("Chatbot")
        # Display chat history
        for i, entry in enumerate(st.session_state.chat_history):
            role = entry["role"].capitalize()
            content = entry["content"]

            if role == "User":
                 st.markdown(f"**{role}:** {content}")
            elif role == "Assistant":
                if isinstance(content, dict): # AnalysisResponse serialized or dict
                     st.markdown(f"**{role}:**")
                     st.write(content.get("answer", ""))
                     if content.get("disclaimer"):
                         st.caption(f"Disclaimer: {content['disclaimer']}")
                     if content.get("related"):
                         with st.container(border=True):
                             st.markdown("Related questions:")
                             for j, r in enumerate(content["related"]):
                                 if st.button(r, key=f"related_{i}_{j}", width="stretch"):
                                     st.session_state["user_chat_input"] = r
                                     st.rerun()
                else:
                    st.markdown(f"**{role}:** {content}")

        # Input box
        user_input = st.chat_input("Ask me about data…", key="user_chat_input")

        if user_input:
            # Validate user input for security
            is_valid, error_msg = code_executor.validate_user_input(user_input)
            if not is_valid:
                st.error(f"Invalid input: {error_msg}")
                return
            
            # Save user message
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            # Build system prompt that tells the assistant to output Python code.
            system_prompt = (
                "You are an assistant that helps data scientists. "
                "Write Python code to answer the user's questions. "
                "You can use `polars` (as `pl`), `pandas` (as `pd`), `geopandas` (as `gpd`), `plotly.express` (as `px`), `plotly.graph_objects` (as `go`), `folium`, and `streamlit` (as `st`). "
                "The code will be executed in the main thread. "
                "All graphs must be created using `plotly` (either `plotly.express` as `px` or `plotly.graph_objects` as `go`). "
                "Always store the result of your analysis in a variable named `result`. "
                "This `result` variable can be a DataFrame (pandas/polars), a plot, or a string/number. "
                "Do not use `print()`. Always store the result of your analysis in a variable named `result`. "
                "When using polars (pl), always enable streaming mode (e.g., `df.collect(streaming=True)`) to keep memory usage low."
            )

            # Check for active uploaded files
            active_dataset_info = ""
            active_parquet_files = []
            if uploaded_files:
                 fk = get_file_key(uploaded_files)
                 if fk in st.session_state:
                     active_dataset_info = st.session_state.get(f"{fk}_info", "")
                     active_parquet_files = st.session_state.get(fk, [])

            if active_parquet_files:
                system_prompt += (
                    "\nYou also have access to an uploaded dataset. "
                    f"The metadata is: {active_dataset_info}\n"
                    f"The parquet files are located at: {active_parquet_files}\n"
                )

            # Call Pydantic AI Agent
            try:
                agent = Agent(
                    st.session_state.llm_model,
                    output_type=AnalysisResponse,
                    system_prompt=system_prompt,
                    model_settings={'temperature': st.session_state.temperature}
                )

                # Using run_sync since streamlit runs in a sync loop mainly, and await might be tricky in standard callbacks
                # or mixed contexts, but st.chat_input triggers rerun.
                result = agent.run_sync(user_input)
                response_data = result.output

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response_data.model_dump()
                })

                # Check for code blocks and execute them
                if response_data.code:
                    code = response_data.code.strip()
                    # Execute code securely with sandboxing
                    global_variables = {}
                    
                    success, error_msg, result = code_executor.execute_code_securely(
                        code=code,
                        global_variables=global_variables,
                        pl=pl, pd=pd, st=st, gpd=gpd, alt=alt, px=px, go=go, folium=folium
                    )
                    
                    if success:
                        if result is not None:
                            st.session_state.last_run_result = copy.deepcopy(result)
                        else:
                            st.error("The generated code did not produce a 'result' variable.")
                    else:
                        st.error(error_msg)

                # Force a rerun to display the new message immediately if not automatic
                st.rerun()

            except Exception as e:
                st.error(f"Error calling assistant: {e}")


    # ---- Analysis panel ----
    with col_analysis:
        st.header("Analysis")
        if st.session_state.last_run_result is not None:
            try:
                display_result(st.session_state.last_run_result)
            except Exception as e:
                st.error(f"Error displaying result: {e}")
        else:
            st.write("Ask a question that requires data and the assistant will fetch & show it here.")

if page == "Home":
    home_page()
else:
    settings_page()
