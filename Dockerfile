# --------------------------------------------------------------
# 1.  Stage 1 – build the image
# --------------------------------------------------------------
FROM python:3.11-slim-bookworm AS build

# Keep the container lean: install only what we need
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgdal-dev \
        libproj-dev \
        libgeos-dev \
        && rm -rf /var/lib/apt/lists/*

# Install pip and requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------------------
# 2.  Stage 2 – runtime image (optional but keeps the image small)
# --------------------------------------------------------------
FROM python:3.11-slim

# Re‑install the compiled libraries that are required at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgeos-c1v5 \
        && rm -rf /var/lib/apt/lists/*

# Copy only the packages we installed in the build stage
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

# Copy the application
WORKDIR /app
COPY app.py .

# Expose the default Streamlit port
EXPOSE 8501

# Streamlit requires the host to be reachable; use 0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true

# Optional: expose secrets via environment variables or a .streamlit/secrets.toml
# Example:
# ENV OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXX
# ENV MCP_ENDPOINT=https://api.my-mcp.com/v1

# Run the Streamlit app
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
