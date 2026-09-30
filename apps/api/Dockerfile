FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-por poppler-utils libpq5 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY apps/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONPATH=/app
COPY apps/api /app
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && python -m app.train_model && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
