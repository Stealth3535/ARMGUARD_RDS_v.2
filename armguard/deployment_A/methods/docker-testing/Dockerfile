# ArmGuard Application Dockerfile for Testing Environment
# Builds a production-like container for comprehensive testing

FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=core.settings_production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
COPY requirements-rpi.txt* ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
    gunicorn \
    psycopg2-binary \
    redis \
    django-redis \
    prometheus-client \
    django-prometheus \
    psutil

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/staticfiles /app/core/media

# Create non-root user for security
RUN groupadd -r armguard && useradd -r -g armguard armguard && \
    chown -R armguard:armguard /app

# Copy and set entrypoint
COPY testing_environment/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Switch to non-root user
USER armguard

# Expose port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "60", "core.wsgi:application"]
