# Multi-arch image: builds natively for linux/amd64 and linux/arm64.
#
# pyatv pulls in miniaudio, which publishes no aarch64 manylinux wheel, so on
# arm64 it must be compiled from its sdist. The compiler lives in this builder
# stage only and never reaches the runtime image.
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Only the lockfile inputs, so the dependency layer survives app source edits.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev


FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

COPY . .
RUN mkdir -p data

EXPOSE 1919

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "1919"]
