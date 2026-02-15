# 🧠 Online Data Scientist

An AI-powered data analysis assistant built with [Streamlit](https://streamlit.io/). Upload your CSV, ZIP, or GZIP files and ask natural language questions about your data. The assistant uses OpenAI's GPT models to generate Python code for analysis and visualization.

## ✨ Features

- **Natural Language Queries:** Ask questions about your data in plain English
- **File Upload Support:** Process CSV, ZIP, and GZIP files automatically
- **Intelligent Data Processing:** 
  - Automatic separator detection (comma, semicolon)
  - Converts large files to chunked Parquet format for efficient querying
  - Progress tracking during file processing
- **Automated Analysis:** AI generates Python code to answer your questions
- **Rich Visualizations:**
  - Interactive tables (pandas/polars DataFrames)
  - Charts using [Plotly](https://plotly.com/python/)
  - Maps using [Folium](https://python-visualization.github.io/folium/)
  - Statistical visualizations with [Altair](https://altair-viz.github.io/)
- **Dual-Pane Interface:** Chat on the left, view results on the right
- **Follow-up Suggestions:** AI suggests related questions to explore your data further
- **Secure Code Execution:** 
  - Sandboxed environment for AI-generated code
  - Timeout protection (prevents infinite loops)
  - Resource limits (memory and CPU constraints)
  - AST validation blocks dangerous operations

## 🛠️ Prerequisites

- **Python 3.11+**
- **OpenAI API Key:** Get one from [OpenAI](https://platform.openai.com/)

## 🚀 Installation & Setup

### Option 1: Local Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install system dependencies (required for GeoPandas):**
   - **Ubuntu/Debian:**
     ```bash
     sudo apt-get install build-essential libgdal-dev libproj-dev libgeos-dev
     ```
   - **macOS (Homebrew):**
     ```bash
     brew install gdal
     ```

3. **Install Python dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Set Environment Variables:**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

5. **Run the application:**
   ```bash
   streamlit run app.py
   ```

### Option 2: Using Docker

1. **Build the Docker image:**
   ```bash
   docker build -t online-data-scientist .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8501:8501 \
     -v $(pwd)/data:/data \
     -e OPENAI_API_KEY="your-openai-api-key" \
     online-data-scientist
   ```

3. Access the app at `http://localhost:8501`.

### Option 3: Run on Mac (Apple Silicon) without building

Pull the pre-built image from GitHub Container Registry:

```bash
docker run -p 8501:8501 \
  -v $(pwd)/data:/data \
  -e OPENAI_API_KEY="your-openai-api-key" \
  ghcr.io/akolk/online-data-scientist:main
```

## ⚙️ Configuration

The application is configured via environment variables and the Settings page:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key for the AI assistant | **Yes** |

### In-App Settings

Access via the **Settings** tab in the app:

- **Parquet Partition Size:** Number of rows per chunk when converting large files (default: 500,000)
- **LLM Model:** OpenAI model to use (default: `openai:gpt-5.2`)
- **Temperature:** Controls response creativity, 0.0 (deterministic) to 2.0 (creative) (default: 0.0)

## 💡 Usage

1. **Open the application** in your browser (`http://localhost:8501`)

2. **Upload your data files:**
   - Click "Upload Data" in the left sidebar
   - Select CSV, ZIP, or GZIP files
   - Multiple files are supported
   - The app automatically:
     - Extracts ZIP/GZIP archives
     - Detects CSV separators
     - Converts to optimized Parquet format
     - Shows processing progress

3. **Ask questions in the chat:**
   - "Show me a summary of the data"
   - "What are the top 10 values in column X?"
   - "Create a bar chart of sales by region"
   - "Calculate the average and standard deviation"

4. **View results:**
   - Tables appear in the Analysis panel
   - Charts render interactively
   - Maps display for geospatial data
   - The AI suggests follow-up questions

## 📁 Supported File Formats

| Format | Description |
|--------|-------------|
| **CSV** | Comma or semicolon-separated values |
| **ZIP** | Archives containing CSV files |
| **GZIP** | Gzip-compressed CSV files |

**Note:** Large files are automatically split into chunks for efficient processing.

## 🔒 Security Features

The app includes comprehensive security measures for executing AI-generated code:

- **Code Validation:** AST parsing blocks dangerous imports and functions
- **Sandboxed Execution:** Restricted Python environment with limited built-ins
- **Timeout Protection:** Code execution limited to 30 seconds (configurable)
- **Resource Limits:** Memory (512 MB default) and CPU time (60s default) constraints
- **Input Validation:** User queries screened for suspicious patterns

**Blocked Operations:**
- File system access (`os`, `open`)
- Network operations (`socket`, `requests`)
- Subprocess execution (`subprocess`, `sys`)
- Code evaluation (`eval`, `exec`, `compile`)
- Serialization (`pickle`, `marshal`)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                        │
│  ┌──────────────┐  ┌────────────────────────────────┐  │
│  │   Chatbot    │  │          Analysis              │  │
│  │  (Questions) │  │  (Tables, Charts, Maps)        │  │
│  └──────────────┘  └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              File Upload & Processing                   │
│         (CSV/ZIP/GZIP → Parquet Conversion)            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Pydantic AI Agent                          │
│    (OpenAI GPT → AnalysisResponse → Python Code)       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Secure Code Executor                       │
│    (AST Validation → Sandboxed Exec → Timeout/Resource │
│                      Limits)                           │
└─────────────────────────────────────────────────────────┘
```

## 🧪 Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io/)
- **AI Framework:** [Pydantic AI](https://github.com/pydantic/pydantic-ai) with OpenAI
- **Data Processing:** [Polars](https://pola.rs/) (primary), [Pandas](https://pandas.pydata.org/) (compatibility)
- **Geospatial:** [GeoPandas](https://geopandas.org/)
- **Visualization:** [Plotly](https://plotly.com/python/), [Altair](https://altair-viz.github.io/), [Folium](https://python-visualization.github.io/folium/)
- **Security:** AST validation, multiprocessing sandbox
- **Containerization:** [Docker](https://www.docker.com/)

## 🧪 Testing

The codebase includes comprehensive tests:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=.
```

**Test Coverage:**
- `data_processor.py`: File extraction, conversion, separator detection
- `code_executor.py`: Security validation, sandboxed execution, timeouts, resource limits
- `app.py`: Helper functions, file key generation, result display

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for rapid UI development
- AI powered by [OpenAI](https://openai.com/)
- Data processing by [Polars](https://pola.rs/)

---

*Built with ❤️ for data enthusiasts.*
