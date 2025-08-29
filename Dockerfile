# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for PDFs etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Expose both ports (API 8000, UI 8501)
EXPOSE 8000 8501

# Default: start API (docker-compose will override CMD per service)
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
