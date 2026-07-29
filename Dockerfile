# syntax=docker/dockerfile:1

FROM python:3.13-alpine@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY requirements.txt .
RUN python -m pip install \
    --no-compile \
    --prefix=/install \
    --require-hashes \
    -r requirements.txt

FROM python:3.13-alpine@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/usr/local/bin:$PATH

RUN addgroup -g 10001 -S planbot \
    && adduser -u 10001 -S -D -H -G planbot -s /sbin/nologin planbot

COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=10001:10001 bot/ bot/
RUN mkdir /app/data && chown 10001:10001 /app/data

USER 10001:10001

HEALTHCHECK --interval=60s --timeout=15s --start-period=20s --retries=3 \
    CMD ["python", "-m", "bot.health"]

CMD ["python", "-m", "bot.main"]
