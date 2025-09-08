FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    unzip \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY arvo/ ./arvo/
COPY pyproject.toml .

# Install Arvo in development mode
RUN pip install -e .

# Copy web UI
COPY arvo/web/ ./web/

# Create directory for deployments
RUN mkdir -p .arvo

# Configure nginx to serve static files and proxy API
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    \
    location / { \
        root /app/web; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
    \
    location /api/ { \
        proxy_pass http://localhost:8080/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
    } \
    \
    location /deploy { \
        proxy_pass http://localhost:8080/deploy; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
    } \
    \
    location /deploy/ { \
        proxy_pass http://localhost:8080/deploy/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
    } \
}' > /etc/nginx/sites-available/default

# Create startup script
RUN echo '#!/bin/bash \
set -e \
\
# Start API server in background \
python -m arvo.api.app & \
API_PID=$! \
\
# Start nginx in foreground \
nginx -g "daemon off;" & \
NGINX_PID=$! \
\
# Wait for either process to exit \
wait $API_PID $NGINX_PID \
' > /app/start.sh && chmod +x /app/start.sh

# Expose port
EXPOSE 80

# Set environment variables
ENV PORT=8080
ENV PYTHONPATH=/app
ENV ARVO_REGION=us-west-2

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Run the startup script
CMD ["/app/start.sh"]
