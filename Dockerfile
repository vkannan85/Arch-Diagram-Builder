FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p diagrams
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/health', timeout=3)"
CMD ["gunicorn","--bind","0.0.0.0:3000","--timeout","120","app_v5:app"]
