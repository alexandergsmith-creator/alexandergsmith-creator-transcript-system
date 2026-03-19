#!/usr/bin/env python3
import json
import time
import logging
import subprocess
import os
import shutil
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

# ================= CONFIG =================
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "14400")) # 4 Hours
KAGGLE_DATASET = os.getenv("KAGGLE_DATASET") 
AUDIO_DIR = Path("audio")
PROCESSED_FILE = Path("processed.json")
CHANNELS_FILE = Path("channels.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Auth Kaggle
api = KaggleApi()
try:
    api.authenticate()
    logging.info("Kaggle Auth: SUCCESS")
except Exception as e:
    logging.error(f"Kaggle Auth Failed: {e}")

def check_dependencies():
    """Verify FFmpeg is installed in the Docker container."""
    if shutil.which("ffmpeg") is None:
        logging.error("CRITICAL: FFmpeg NOT FOUND! Ensure Dockerfile is working.")
        return False
    return True

def download_audio(video_id):
    output = str(AUDIO_DIR / "audio.wav")
    # Clean up before starting
    for f in AUDIO_DIR.glob("*"): os.remove(f)
    
    cmd = [
        "yt-dlp", "-x", "--audio-format", "wav",
        "--ffmpeg-location", "/usr/bin/ffmpeg",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "-o", output, f"https://youtube.com/watch?v={video_id}"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Download Error: {result.stderr}")
        return False
    return True

def upload(video_id):
    try:
        api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {video_id}", dir_mode='zip')
        return True
    except Exception as e:
        logging.error(f"Upload error: {e}")
        return False

# ================= MAIN LOOP =================
if check_dependencies():
    while True:
        try:
            # Load channels
            with open(CHANNELS_FILE) as f: channels = json.load(f)
            
            # Simple single-pass logic to save trial credits
            for channel in channels:
                # Get latest video ID
                res = subprocess.run(["yt-dlp", "--get-id", "--playlist-end", "1", channel], capture_output=True, text=True)
                vid = res.stdout.strip()
                
                # Check if processed
                processed = []
                if PROCESSED_FILE.exists():
                    with open(PROCESSED_FILE) as f: processed = json.load(f)
                
                if vid and vid not in processed:
                    logging.info(f"New video found: {vid}")
                    if download_audio(vid):
                        if upload(vid):
                            processed.append(vid)
                            with open(PROCESSED_FILE, "w") as f: json.dump(processed, f)
                            logging.info(f"Success! {vid} sent to Kaggle.")
            
            logging.info(f"Sleeping {POLL_INTERVAL}s...")
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            logging.error(f"Loop error: {e}")
            time.sleep(60)
