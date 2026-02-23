FROM python:3.11-slim

# Create a non-root user
RUN groupadd -r healthcheck && useradd -r -g healthcheck healthcheck

# Set working directory
WORKDIR /app

# Install system dependencies required for psutil & psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app/ ./app/

# Change ownership to non-root user
RUN chown -R healthcheck:healthcheck /app

# Switch to non-root user
USER healthcheck

# Expose API port
EXPOSE 8000

# Set environment variable defaults
ENV PORT=8000
ENV PYTHONPATH=/app

# Production-ready CMD
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
