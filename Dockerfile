FROM python:3.11-slim-bookworm

COPY --chown=10001:10001 backend/ /app/

RUN apt-get update \
    && apt-get upgrade -y \
    && python -m pip install --no-cache-dir --upgrade setuptools wheel \
    && python -m pip install --no-cache-dir -r /app/requirements.txt \
    && groupadd -g 10001 appgroup \
    && useradd -u 10001 -g appgroup -M appuser \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

USER appuser

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]