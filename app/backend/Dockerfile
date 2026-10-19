FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ai_core.py ai_engine.py ai_chat.py courier_sim.py db_layer.py security.py metrics.py ./

EXPOSE 5000

CMD ["python", "app.py"]
