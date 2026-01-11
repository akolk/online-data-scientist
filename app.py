import os
import json
import re
import sys
import io
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
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from typing import List, Optional

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

def display_result(result):
    """
    Render the result in the right column.
    Handles DataFrames, Charts, Maps, and text.
    """
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


# ----------------------------------------------------------------------
# 3️⃣  Streamlit UI
# ----------------------------------------------------------------------
st.set_page_config(page_title="🧠 Online Data Scientist", layout="wide")

# Progress bar container in the header
progress_bar_placeholder = st.empty()

st.title("🧠 Online Data Scientist")

# Session state to keep the chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "last_run_result" not in st.session_state:
    st.session_state.last_run_result = None

# Sidebar for file upload
with st.sidebar:
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Choose a ZIP or GZIP file", type=["zip", "gz", "gzip"])

    if uploaded_file is not None:
        # Check if already processed to avoid re-processing on every rerun
        # We use file.file_id or name+size as key.
        file_key = f"processed_{uploaded_file.name}_{uploaded_file.size}"

        if file_key not in st.session_state:
            st.info("Processing file...")

            # Progress bar logic
            progress_bar = progress_bar_placeholder.progress(0, text="Starting extraction...")

            def update_progress(p):
                # Update the progress bar
                progress_bar.progress(int(p * 100), text=f"Processing... {int(p*100)}%")

            # Create a temporary directory
            temp_dir = tempfile.mkdtemp()
            # Store temp_dir in session state to allow cleanup later if needed
            if "temp_dirs" not in st.session_state:
                st.session_state.temp_dirs = []
            st.session_state.temp_dirs.append(temp_dir)

            try:
                # Process
                parquet_files = data_processor.extract_and_convert(
                    uploaded_file,
                    uploaded_file.name,
                    temp_dir,
                    update_progress
                )

                if not parquet_files:
                    st.error("No valid data could be extracted from the uploaded file.")
                    # Clean up since we failed to get data
                    shutil.rmtree(temp_dir, ignore_errors=True)
                else:
                    st.session_state[file_key] = parquet_files
                    # Extract metadata
                    dataset_info = data_processor.get_dataset_info(parquet_files)
                    st.session_state[f"{file_key}_info"] = dataset_info
                    st.success(f"Processed {len(parquet_files)} parquet files.")

                # Clear progress bar
                progress_bar.empty()

            except Exception as e:
                st.error(f"Error processing file: {e}")
                progress_bar.empty()
                # Clean up on failure
                shutil.rmtree(temp_dir, ignore_errors=True)

        # If processed, load it into analysis result
        if file_key in st.session_state:
            parquet_files = st.session_state[file_key]
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
            "Do not use `print()`. Always store the result of your analysis in a variable named `result`."
        )

        # Check for active uploaded file
        active_dataset_info = ""
        active_parquet_files = []
        if uploaded_file:
             fk = f"processed_{uploaded_file.name}_{uploaded_file.size}"
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
                'openai:gpt-5.2',
                output_type=AnalysisResponse,
                system_prompt=system_prompt
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
                # Execute code
                global_variables = {}

                try:
                    exec(code, {'pl': pl, 'pd': pd, 'st': st, 'gpd': gpd, 'alt': alt, 'px': px, 'go': go, 'folium': folium}, global_variables)

                    if 'result' in global_variables:
                        st.session_state.last_run_result = copy.deepcopy(global_variables['result'])
                except Exception as e:
                    st.error(f"Error executing code: {e}")
                    # We might want to add error to history, or just show ephemeral error
                    # st.session_state.chat_history.append({"role": "system", "content": f"Error executing code: {e}"})

            # Force a rerun to display the new message immediately if not automatic
            st.rerun()

        except Exception as e:
            st.error(f"Error calling assistant: {e}")


# ---- Analysis panel ----
with col_analysis:
    st.header("Analysis")
    if st.session_state.last_run_result is not None:
        display_result(st.session_state.last_run_result)
    else:
        st.write("Ask a question that requires data and the assistant will fetch & show it here.")
