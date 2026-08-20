FROM python:3.11-slim

WORKDIR /app

COPY requirements-backend.txt ./requirements-backend.txt
RUN pip install --no-cache-dir -r requirements-backend.txt

COPY app ./app
COPY configs ./configs

CMD ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
