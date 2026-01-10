import os
import json
import requests
import streamlit as st
from openai import OpenAI
import pandas as pd
import geopandas as gpd
import altair as alt
import plotly.express as px
import folium
from streamlit_folium import st_folium
import polars as pl
import tempfile
import shutil
import data_processor

# ----------------------------------------------------------------------
# 1️⃣  Configuration – read secrets from environment
# ----------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MCP_ENDPOINT   = os.getenv("MCP_ENDPOINT")      # e.g. https://api.my-mcp.com/v1
MCP_API_KEY    = os.getenv("MCP_API_KEY", "")   # optional

if not OPENAI_API_KEY:
    st.error("❌ `OPENAI_API_KEY` is missing. Please set it in your environment.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------------------------------------------------
# 2️⃣  Helper functions
# ----------------------------------------------------------------------
def call_openai_chat(messages, model="gpt-4o-mini", temperature=0.3):
    """Send a list of messages to OpenAI and return the assistant reply."""
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages
    )
    return response.choices[0].message.content.strip()


def fetch_from_mcp(query_dict):
    """
    Send a request to the MCP server.
    The query_dict should contain at least:
        - endpoint : str  (e.g. "/datasets/US_GDP")
        - params   : dict (query parameters)
    """
    url = f"{MCP_ENDPOINT}{query_dict['endpoint']}"
    headers = {"Authorization": f"Bearer {MCP_API_KEY}"} if MCP_API_KEY else {}
    resp = requests.get(url, headers=headers, params=query_dict.get("params", {}))
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return resp.json()
    elif "text/csv" in content_type or ".csv" in url:
        return pd.read_csv(pd.compat.StringIO(resp.text))
    else:
        # fallback – try to interpret as CSV
        return pd.read_csv(pd.compat.StringIO(resp.text))


def render_analysis(data, data_type="pandas"):
    """
    Render the data in the right column.
    * `data` can be a pandas.DataFrame or a geopandas.GeoDataFrame.
    * `data_type` can be 'pandas' or 'geopandas'.
    """
    if data_type == "geopandas" and isinstance(data, gpd.GeoDataFrame):
        # Simple folium map – show centroids
        m = folium.Map(location=[data.geometry.y.mean(), data.geometry.x.mean()],
                       zoom_start=5)
        for _, row in data.iterrows():
            folium.GeoJson(row.geometry).add_to(m)
        st_folium(m, width=700)
    elif isinstance(data, pd.DataFrame):
        # Show table
        st.dataframe(data.head(20))
        # Try to plot the first two numeric columns
        numeric_cols = data.select_dtypes(include="number").columns.tolist()
        if len(numeric_cols) >= 2:
            chart = alt.Chart(data).mark_point().encode(
                x=numeric_cols[0],
                y=numeric_cols[1]
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
        elif len(numeric_cols) == 1:
            chart = px.line(data, y=numeric_cols[0])
            st.plotly_chart(chart, use_container_width=True)
    else:
        st.write("No renderable data available.")


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

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

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

                    st.session_state.analysis_result = {"df": df_pandas, "type": "pandas"}
                    st.success("Data loaded into Analysis view.")
                except Exception as e:
                    st.error(f"Failed to load data: {e}")


# Two‑column layout: chat | analysis
col_chat, col_analysis = st.columns([4, 6])

# ---- Chat panel ----
with col_chat:
    st.header("Chatbot")
    # Display chat history
    for entry in st.session_state.chat_history:
        role = entry["role"].capitalize()
        st.markdown(f"**{role}:** {entry['content']}")

    # Input box
    user_input = st.text_input("You:", key="user_input", placeholder="Ask me about data…")
    if st.button("Send", key="send_btn") and user_input:
        # Save user message
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Build system prompt that tells the assistant to output a *JSON plan* if data is needed.
        system_prompt = (
            "You are an assistant that helps data scientists. "
            "When a user asks for data, respond with a JSON object that contains "
            "the following fields (if data is needed):\n"
            "- `fetch`: object with `endpoint` (string) and optional `params` (object)\n"
            "- `description`: human‑readable explanation of what the data represents.\n"
            "If no data is required, just give a normal answer."
        )

        # Call OpenAI
        assistant_reply = call_openai_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )

        st.session_state.chat_history.append({"role": "assistant", "content": assistant_reply})

        # ---------- Try to parse JSON request ----------
        try:
            parsed = json.loads(assistant_reply)
        except json.JSONDecodeError:
            parsed = None

        if parsed and isinstance(parsed, dict) and "fetch" in parsed:
            # 1️⃣  Fetch data from MCP
            fetch_dict = parsed["fetch"]
            try:
                raw = fetch_from_mcp(fetch_dict)
                # 2️⃣  Convert to GeoDataFrame if geometry exists
                if isinstance(raw, pd.DataFrame) and "geometry" in raw.columns:
                    gdf = gpd.GeoDataFrame(
                        raw, geometry=gpd.GeoSeries.from_wkt(raw.geometry)
                    )
                    st.session_state.analysis_result = {"df": gdf, "type": "geopandas"}
                else:
                    st.session_state.analysis_result = {"df": raw, "type": "pandas"}
            except Exception as e:
                st.session_state.analysis_result = None
                st.error(f"❌ Data fetch failed: {e}")

        else:
            st.session_state.analysis_result = None

# ---- Analysis panel ----
with col_analysis:
    st.header("Analysis")
    if st.session_state.analysis_result:
        render_analysis(
            st.session_state.analysis_result["df"],
            st.session_state.analysis_result["type"]
        )
    else:
        st.write("Ask a question that requires data and the assistant will fetch & show it here.")
