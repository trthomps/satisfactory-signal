# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml .

# Install dependencies with uv from pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv && \
    uv pip install --python=/opt/venv/bin/python -r pyproject.toml

FROM gcr.io/distroless/python3-debian12:nonroot

WORKDIR /app

COPY --from=builder /opt/venv/lib/python3.12/site-packages /app/.venv
COPY *.py .

ENV PYTHONPATH=/app/.venv

CMD ["main.py"]
