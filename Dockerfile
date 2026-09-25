FROM python:3.12-slim
RUN apt-get update && apt-get install -y graphviz graphviz-dev gcc pkg-config && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p diagrams
CMD ["gunicorn","--bind","0.0.0.0:3000","--timeout","120","app_rebuilt:app"]
