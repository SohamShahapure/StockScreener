# Optional container image for the backend - use this instead of Render's
# native Python runtime if you prefer Docker (Render, Railway, Fly.io, etc.
# all accept it). Build context is the `backend/` directory.
FROM python:3.11-slim

# System deps: build-essential is needed by some wheels; curl for healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY . .

# Persist the vector store + model cache under /var/data (mount a volume here).
ENV CHROMA_PERSIST_DIR=/var/data/chroma_db \
    HF_HOME=/var/data/hf-cache \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# $PORT is provided by most PaaS hosts; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
