FROM python:3.11-slim
WORKDIR /app
COPY app/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/frontend /app/frontend
COPY app/backend /app/backend
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1
EXPOSE 5000
CMD ["python", "app.py"]
