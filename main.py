#!/usr/bin/env python3
import os

# --- STEP 1: FORCE AUTH BEFORE KAGGLE LOADS ---
# This stops the "Could not find kaggle.json" error.
os.environ['KAGGLE_API_TOKEN'] = os.getenv('KAGGLE_API_TOKEN', '')

import json
import time
import logging
import subprocess
from pathlib import Path

# Now we can safely import Kaggle
try:
    from kaggle.api.kaggle_api_extended import KaggleApi
    KAGGLE_AVAILABLE = True
except Exception as e:
    print(f"Kaggle Import Error: {e}")
    KAGGLE_AVAILABLE = False

# --- STEP 2: FIX FFMPEG ---
try:
    from static_ffmpeg import add_paths
    add_paths()
    FFMPEG_READY = True
except ImportError:
    FFMPEG_READY = False

# ================= CONFIG =================
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "14400"))
# IMPORTANT: Ensure this is 'username/dataset-name' in Railway
KAGGLE_DATASET = os.getenv("KAGGLE_DATASET") 
AUDIO_DIR = Path("audio")
PROCESSED_FILE = Path("processed.json")
CHANNELS_FILE = Path("channels.json")

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s]: %(message)s"
)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Initialize Kaggle
api = KaggleApi()
if KAGGLE_AVAILABLE:
    try:
        api.authenticate()
        logging.info("Kaggle Auth: SUCCESS")
    except Exception as e:
        logging.error(f"Kaggle Auth Failed: {e}")

def download_audio(video_id):
    output = str(AUDIO_DIR / "audio.wav")
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
    return result.returncode == 0

def upload(video_id):
    if not KAGGLE_DATASET or "http" in KAGGLE_DATASET:
        logging.error("KAGGLE_DATASET must be 'username/slug', not a URL!")
        return False
    try:
        logging.info(f"Pushing {video_id} to Kaggle...")
        api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {video_id}", dir_mode='zip')
        return True
    except Exception as e:
        logging.error(f"Kaggle Upload Failed: {e}")
        return False

# ================= MAIN LOOP =================
logging.info("Scout Service Active.")

while True:
    try:
        if not CHANNELS_FILE.exists():
            logging.error("channels.json missing!")
            time.sleep(60)
            continue
            
        with open(CHANNELS_FILE) as f: 
            channels = json.load(f)
        
        processed = []
        if PROCESSED_FILE.exists():
            with open(PROCESSED_FILE) as f: 
                data = json.load(f)
                processed = data if isinstance(data, list) else []

        for channel in channels:
            res = subprocess.run(["yt-dlp", "--get-id", "--playlist-end", "1", channel], capture_output=True, text=True)
            vid = res.stdout.strip()
            
            if vid and vid not in processed:
                logging.info(f"New video: {vid}")
                if download_audio(vid):
                    if upload(vid):
                        processed.append(vid)
                        with open(PROCESSED_FILE, "w") as f: 
                            json.dump(processed, f)
                        logging.info(f"Done: {vid}")
        
        logging.info(f"Cycle complete. Sleeping {POLL_INTERVAL}s.")
        time.sleep(POLL_INTERVAL)

    except Exception as e:
        logging.error(f"Loop error: {e}")
        time.sleep(60)
