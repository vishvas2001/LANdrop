FROM python:3.12-slim

# Copy uv binary from official image for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first for Docker layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source and install the package
COPY README.md ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# Persist SQLite database and uploaded files outside the ephemeral container layer
RUN mkdir -p /app/data/uploads
ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "src/landrop/main.py", "--host", "0.0.0.0", "--port", "8000"]