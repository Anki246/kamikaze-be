# FluxTrader Backend - Production Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV USE_AWS_SECRETS=true
ENV AWS_DEFAULT_REGION=us-east-1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r fluxtrader && useradd -r -g fluxtrader fluxtrader

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies including AWS SDK
RUN pip install --no-cache-dir -r requirements.txt boto3

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p logs data && \
    chown -R fluxtrader:fluxtrader /app

# Production environment variables will be set via GitHub secrets
# No .env file needed in production - all config via environment variables

# Switch to non-root user
USER fluxtrader

# Expose port
EXPOSE 8000

# Health check with proper endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with production settings
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
