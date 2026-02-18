"""Online Data Scientist - AI-powered data analysis application.

This package provides a Streamlit-based web application that uses OpenAI's GPT
models to perform data analysis through natural language queries. The application
supports CSV, ZIP, and GZIP file uploads, converts them to Parquet format for
efficient processing, and executes Python code securely in a sandboxed environment.

Main Modules:
    app: Main Streamlit application entry point
    data_processor: File extraction and Parquet conversion utilities
    code_executor: Secure code execution with sandboxing
    validators: Input validation functions
    logging_config: Centralized logging configuration
    settings_storage: Persistent settings management

Pages:
    pages.Settings: Settings page for configuration management

Example:
    To run the application::

        $ streamlit run app.py

    To run tests::

        $ pytest tests/

Attributes:
    __version__: Package version string
    __author__: Package author

See Also:
    - README.md for detailed documentation
    - pyproject.toml for project configuration
"""

__version__ = "1.0.0"
__author__ = "OpenCode"

# Define what should be imported with "from online_data_scientist import *"
__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Main modules (explicit re-exports for convenience)
    "app",
    "data_processor",
    "code_executor",
    "validators",
    "logging_config",
    "settings_storage",
]
