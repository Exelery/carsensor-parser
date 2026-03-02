FROM python:3.12-slim

WORKDIR /app
COPY backend ./backend
COPY worker/requirements.txt worker/run_worker.py ./
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONPATH=/app/backend
CMD ["python", "run_worker.py"]
