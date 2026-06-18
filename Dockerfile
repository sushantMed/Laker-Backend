FROM python:3.12-slim

WORKDIR /app

# System deps: libpq for asyncpg, netcat-openbsd for DB readiness check
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=100 -r requirements.txt

COPY . .

# Ensure entrypoint script is executable
RUN chmod +x /app/docker-entrypoint.sh && \
    ls -la /app/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
