FROM python:3.11.10-slim-bookworm

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd -g 10001 appgroup \
    && useradd -u 10001 -g appgroup -M appuser

COPY --chown=appuser:appgroup backend/ /app/

USER appuser

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]