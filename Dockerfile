# syntax=docker/dockerfile:1

# Use Python 3.14 free-threaded build for true parallelism (no GIL)
FROM python:3.14t-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml .

# Install dependencies with uv, using cache mount for speed
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv && \
    uv pip install --python=/opt/venv/bin/python \
    pysignalclirestapi requests python-dotenv websockets emoji

# Use slim image for runtime (distroless doesn't support free-threaded Python)
FROM python:3.14t-slim

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app
USER app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app *.py .

ENV PYTHONPATH=/opt/venv/lib/python3.14t/site-packages
# Disable GIL for true multi-threaded parallelism
ENV PYTHON_GIL=0
# Enable JIT compiler for performance
ENV PYTHON_JIT=1

CMD ["python", "main.py"]
