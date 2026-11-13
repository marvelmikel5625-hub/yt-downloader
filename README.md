# yt-downloader

Local YouTube downloader: paste a link, pick a quality, get the file.

## ⚠️ Legal
This project is for **personal, local use only**. Downloading YouTube videos
violates YouTube's Terms of Service. Do not deploy this publicly. You are
responsible for how you use it.

## Run with Docker
    docker build -t yt-downloader .
    docker run -p 5000:5000 yt-downloader
    # open http://localhost:5000

## Run locally
    pip install -r requirements.txt
    # ffmpeg must be installed (apt install ffmpeg / brew install ffmpeg)
    python app.py
