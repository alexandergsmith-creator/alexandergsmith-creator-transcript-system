#!/usr/bin/env python3
import os
import json
import time
import logging
import subprocess
import shutil
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

# --- THE MAGIC LINK ---
# This downloads a portable FFmpeg automatically so Railway doesn't have to provide it.
try:
    from static_ffmpeg import add_paths
    add_paths()
    logging.info("Internal FFmpeg: READY")
except ImportError:
    logging.warning("static-ffmpeg not found, attempting system FFmpeg")

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

def download_audio(video_id):
    output = str(AUDIO_DIR / "audio.wav")
    # Clean up local storage before starting
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
        logging.error(f"Download Error: {result.stderr}")
        return False
    return True

def upload(video_id):
    if not KAGGLE_DATASET:
        logging.error("KAGGLE_DATASET variable is missing!")
        return False
    try:
        logging.info(f"Pushing {video_id} to Kaggle...")
        api.dataset_create_version(str(AUDIO_DIR), version_notes=f"New Audio: {video_id}", dir_mode='zip')
        return True
    except Exception as e:
        logging.error(f"Kaggle Upload Failed: {e}")
        return False

# ================= MAIN LOOP =================
logging.info("Scout Service Active (Nuclear Mode).")

while True:
    try:
        # Load channels from your JSON file
        if not CHANNELS_FILE.exists():
            logging.error("channels.json NOT FOUND!")
            time.sleep(60)
            continue
            
        with open(CHANNELS_FILE) as f: 
            channels = json.load(f)
        
        # Check for processed videos
        processed = []
        if PROCESSED_FILE.exists():
            with open(PROCESSED_FILE) as f: 
                data = json.load(f)
                processed = data if isinstance(data, list) else []

        for channel in channels:
            # Get the ID of the single latest video
            res = subprocess.run(["yt-dlp", "--get-id", "--playlist-end", "1", channel], capture_output=True, text=True)
            vid = res.stdout.strip()
            
            if vid and vid not in processed:
                logging.info(f"Target found: {vid}")
                if download_audio(vid):
                    if upload(vid):
                        processed.append(vid)
                        with open(PROCESSED_FILE, "w") as f: 
                            json.dump(processed, f)
                        logging.info(f"Success! {vid} is now in your Kaggle dataset.")
        
        logging.info(f"Cycle complete. Sleeping {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)

    except Exception as e:
        logging.error(f"Global Error: {e}")
        time.sleep(60)
