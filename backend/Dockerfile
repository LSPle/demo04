# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set workdir
WORKDIR /app

# System deps (optional, keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (leverage Docker layer caching)
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# CloudBase Run listens on 8080 by default
ENV PORT=8080
EXPOSE 8080

# Start with gunicorn loading the WSGI app defined in app/wsgi.py
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app.wsgi:app"]