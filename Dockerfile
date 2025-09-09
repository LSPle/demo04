# Multi-stage build for frontend and backend
# Stage 1: Build frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY front/package*.json ./
RUN npm ci --only=production
COPY front/ ./
RUN npm run build

# Stage 2: Backend with frontend static files
FROM python:3.10-slim AS production

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
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Copy backend application code
COPY backend/ ./

# Copy frontend build files
COPY --from=frontend-build /app/frontend/build ./build

# CloudBase Run listens on 8080 by default
ENV PORT=8080
EXPOSE 8080

# Start with gunicorn loading the WSGI app defined in app/wsgi.py
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app.wsgi:app"]