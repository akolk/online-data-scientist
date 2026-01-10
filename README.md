# 🧠 Online Data Scientist

**Online Data Scientist** is an intelligent assistant that acts as a bridge between you and your data. Built with [Streamlit](https://streamlit.io/), it leverages OpenAI's GPT models to understand your questions, fetches relevant data from a Model Context Protocol (MCP) endpoint, and visualizes it instantly.

## ✨ Features

- **Interactive Chatbot:** Communicate naturally with an AI assistant powered by OpenAI.
- **Intelligent Data Fetching:** The assistant determines when to fetch data based on your query and retrieves it from a configured MCP endpoint.
- **Automated Visualization:**
  - **Tabular Data:** View data in interactive tables.
  - **Geospatial Data:** Automatically detects geometry columns and renders interactive maps using [Folium](https://python-visualization.github.io/folium/).
  - **Charts:** Generates charts for numeric data using [Altair](https://altair-viz.github.io/) and [Plotly](https://plotly.com/python/).
- **Dual-Pane Interface:** Chat on the left, visualize results on the right.

## 🛠️ Prerequisites

Before you begin, ensure you have the following:

- **Python 3.11+**
- **OpenAI API Key**: You need an active API key from [OpenAI](https://platform.openai.com/).
- **MCP Endpoint**: A URL to a Model Context Protocol server (or compatible API) that serves your data.

## 🚀 Installation & Setup

You can run the application locally or using Docker.

### Option 1: Local Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install system dependencies (required for GeoPandas):**
    *   **Ubuntu/Debian:**
        ```bash
        sudo apt-get install build-essential libgdal-dev libproj-dev libgeos-dev
        ```
    *   **macOS (Homebrew):**
        ```bash
        brew install gdal
        ```

3.  **Install Python dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

4.  **Set Environment Variables:**
    Export the required variables in your shell or create a `.env` file (if you have `python-dotenv` installed, otherwise set them manually).
    ```bash
    export OPENAI_API_KEY="your-openai-api-key"
    export MCP_ENDPOINT="https://api.your-mcp-server.com/v1"
    # Optional
    export MCP_API_KEY="your-mcp-api-key"
    ```

5.  **Run the application:**
    ```bash
    streamlit run app.py
    ```

### Option 2: Using Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t online-data-scientist .
    ```

2.  **Run the container:**
    Replace the placeholder values with your actual keys and endpoint.
    ```bash
    docker run -p 8501:8501 \
      -e OPENAI_API_KEY="your-openai-api-key" \
      -e MCP_ENDPOINT="https://api.your-mcp-server.com/v1" \
      -e MCP_API_KEY="your-mcp-api-key" \
      online-data-scientist
    ```

3.  Access the app at `http://localhost:8501`.

## ⚙️ Configuration

The application is configured via environment variables:

| Variable | Description | Required |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | Your OpenAI API key for the chatbot. | **Yes** |
| `MCP_ENDPOINT` | Base URL of the MCP server to fetch data from. | **Yes** |
| `MCP_API_KEY` | API key for the MCP server (if authentication is needed). | No |

## 💡 Usage

1.  Open the application in your browser.
2.  In the **Chatbot** panel (left), ask a question like:
    *   "Show me the GDP of the US for the last 10 years."
    *   "Can you map the locations of recent sales?"
    *   "Get the user demographics data."
3.  The assistant will interpret your request. If it needs data, it will fetch it from the `MCP_ENDPOINT`.
4.  The retrieved data will be displayed in the **Analysis** panel (right) as a table, chart, or map.

## 🏗️ Tech Stack

-   **Frontend:** [Streamlit](https://streamlit.io/)
-   **AI Logic:** [OpenAI API](https://platform.openai.com/docs/api-reference)
-   **Data Manipulation:** [Pandas](https://pandas.pydata.org/), [GeoPandas](https://geopandas.org/)
-   **Visualization:** [Altair](https://altair-viz.github.io/), [Plotly](https://plotly.com/python/), [Folium](https://python-visualization.github.io/folium/)
-   **Containerization:** [Docker](https://www.docker.com/)

---

*Built with ❤️ for data enthusiasts.*
