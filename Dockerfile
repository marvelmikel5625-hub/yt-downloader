FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py index.html ./
EXPOSE 5000
# update yt-dlp on every container start so extractors stay fresh
CMD ["sh", "-c", "pip install -q -U yt-dlp && gunicorn -b 0.0.0.0:5000 -w 2 --threads 8 app:app"]
