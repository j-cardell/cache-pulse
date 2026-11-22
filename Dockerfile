# cache-pulse — stdlib-only Python, no pip installs required
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY templates/ ./templates/

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HF_HOME=/caches/huggingface \
    TORCH_HOME=/caches/torch \
    PODMAN_SOCKET=/run/podman/podman.sock

VOLUME ["/app/out"]
EXPOSE 8080

CMD ["python", "-m", "cache_pulse", "serve", "--host", "0.0.0.0", "--port", "8080"]
