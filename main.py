#!/usr/bin/env python3
import os
import json
import time
import logging
import subprocess
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

# --- 1. KAGGLE AUTH FIX ---
# This pulls your token from Railway Variables so it doesn't crash
os.environ['KAGGLE_API_TOKEN'] = os.getenv('KAGGLE_API_TOKEN', '')

# --- 2. THE FFmpeg FIX ---
# This downloads a portable FFmpeg so Railway doesn't have to provide it
try:
    from static_ffmpeg import add_paths
    add_paths()
    logging.info("Internal FFmpeg: READY")
except ImportError:
    logging.warning("static-ffmpeg not found in requirements.txt")

# ================= CONFIG =================
# 14400s = 4 hours. This keeps your usage extremely low (Forever Free)
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "14400"))
KAGGLE_DATASET = os.getenv("KAGGLE_DATASET") 
AUDIO_DIR = Path("audio")
PROCESSED_FILE = Path("processed.json")
CHANNELS_FILE = Path("channels.json")

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s]: %(message)s"
)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Initialize Kaggle API
api = KaggleApi()
try:
    api.authenticate()
    logging.info("Kaggle Auth: SUCCESS")
except Exception as e:
    logging.error(f"Kaggle Auth Failed: {e}")

def download_audio(video_id):
    output = str(AUDIO_DIR / "audio.wav")
    # Clean up the folder before every download
    for f in AUDIO_DIR.glob("*"): 
        try: os.remove(f)
        except: pass
    
    logging.info(f"Downloading: {video_id}")
    cmd = [
        "yt-dlp", "-x", "--audio-format", "wav",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "-o", output, f"https://youtube.com/watch?v={video_id}"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"YT-DLP Error: {result.stderr}")
        return False
    return True

def upload(video_id):
    if not KAGGLE_DATASET:
        logging.error("Missing KAGGLE_DATASET variable in Railway!")
        return False
    try:
        logging.info(f"Uploading {video_id} to Kaggle...")
        # version_notes helps you track which video was last processed
        api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {video_id}", dir_mode='zip')
        return True
    except Exception as e:
        logging.error(f"Kaggle Upload Failed: {e}")
        return False

# ================= MAIN LOOP =================
logging.info("Scout Service Active. Monitoring channels...")

while True:
    try:
        if not CHANNELS_FILE.exists():
            logging.error("channels.json is missing from your repo!")
            time.sleep(60)
            continue
            
        with open(CHANNELS_FILE) as f: 
            channels = json.load(f)
        
        processed = []
        if PROCESSED_FILE.exists():
            with open(PROCESSED_FILE) as f: 
                data = json.load(f)
                # Ensure we handle the file correctly if it's empty
                processed = data if isinstance(data, list) else []

        for channel in channels:
            # Check for the newest video ID
            res = subprocess.run(["yt-dlp", "--get-id", "--playlist-end", "1", channel], capture_output=True, text=True)
            vid = res.stdout.strip()
            
            if vid and vid not in processed:
                logging.info(f"New target found: {vid}")
                if download_audio(vid):
                    if upload(vid):
                        processed.append(vid)
                        with open(PROCESSED_FILE, "w") as f: 
                            json.dump(processed, f)
                        logging.info(f"Success! {vid} is now on Kaggle.")
        
        logging.info(f"Cycle complete. Hibernating for {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)

    except Exception as e:
        logging.error(f"Main Loop Error: {e}")
        time.sleep(60)
