FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY input_service/requirements.txt /app/input_service/requirements.txt
RUN pip install --no-cache-dir -r /app/input_service/requirements.txt

COPY input_service /app/input_service
COPY football_analysis /app/football_analysis

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "input_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
