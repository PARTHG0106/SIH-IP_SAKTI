# IP-SAKTI Sahayak — portable single-worker container image.
# Runs the FastAPI app that also serves the frontend at the same origin.
FROM python:3.12-slim

# Faster, quieter Python in containers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what the running service needs (no tests/docs/scripts/secrets).
COPY backend/ backend/
COPY frontend/ frontend/
COPY corpus/ corpus/
COPY config/ config/

# Ephemeral audit/consent log dir (contents are not persisted across redeploys).
RUN mkdir -p logs

# The app must run as a SINGLE worker: chat memory + the TTL sweeper live in
# process. Bind to the platform-provided $PORT (Render/Cloud Run/Railway/Fly).
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
