# API image. Installs exact versions from uv.lock and leaves out the training libraries.
# The frozen model is not copied in: docker-compose.yml mounts it read-only at run time.
FROM python:3.11-slim

# XGBoost needs the OpenMP runtime, which the slim image does not include.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "uv==0.8.*"

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-default-groups --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

# Run as an ordinary user, so a compromised process cannot change the application files.
RUN useradd --create-home --uid 1001 finguard
USER finguard

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=4)"]

# Uvicorn trusts X-Forwarded-For from 127.0.0.1 by default. Turning that off leaves proxy trust
# to TRUSTED_PROXY_IPS alone, which is empty unless deliberately configured.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
