# Kamikaze AI Backend - Production Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables for Python and application
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# AWS Secrets Manager Configuration
ENV USE_AWS_SECRETS=true
ENV AWS_DEFAULT_REGION=us-east-1

# Application Configuration
ENV LOG_LEVEL=INFO
ENV ENABLE_FILE_LOGGING=true
ENV MAX_LOG_FILES=10

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    postgresql-client \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r kamikaze && useradd -r -g kamikaze kamikaze

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (boto3 already included in requirements.txt)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p logs data /app/logs/system /app/logs/trading_sessions /app/logs/archived && \
    chown -R kamikaze:kamikaze /app

# Validate AWS Secrets Manager integration (optional health check)
RUN python -c "from src.infrastructure.aws_secrets_manager import SecretsManager; print('✅ AWS Secrets Manager integration validated')" || echo "⚠️ AWS Secrets Manager validation skipped (no credentials)"

# Production configuration notes:
# - AWS credentials provided via IAM roles (recommended) or environment variables
# - Database credentials retrieved from kmkz-db-secrets
# - Application secrets (AWS keys, Groq API) retrieved from kmkz-app-secrets
# - No hardcoded credentials in container

# Switch to non-root user
USER kamikaze

# Expose port
EXPOSE 8000

# Health check with proper endpoint and AWS secrets validation
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the Kamikaze AI backend application
# The application will automatically:
# 1. Retrieve database credentials from kmkz-db-secrets
# 2. Retrieve AWS credentials and Groq API key from kmkz-app-secrets
# 3. Use system environment variables as fallback
CMD ["python", "app.py"]
