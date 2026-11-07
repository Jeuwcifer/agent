FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY context/ ./context/
COPY cloud_run_translate.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "cloud_run_translate.py"]
