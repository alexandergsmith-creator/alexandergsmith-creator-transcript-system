#!/usr/bin/env python3
import os
import json
import time
import logging
import subprocess
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

# --- 1. ENVIRONMENT & AUTH FIX ---
# This forces Kaggle to use your Railway Variables instead of a file
os.environ['KAGGLE_USERNAME'] = os.getenv('KAGGLE_USERNAME', '')
os.environ['KAGGLE_KEY'] = os.getenv('KAGGLE_KEY', '')

# --- 2. THE NUCLEAR FFmpeg OPTION ---
# This downloads a portable FFmpeg so you don't need Docker/Nixpacks settings
try:
    from static_ffmpeg import add_paths
    add_paths()
    logging.info("Internal FFmpeg: READY")
except ImportError:
    logging.warning("static-ffmpeg not installed in requirements.txt")

# ================= CONFIG =================
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "14400")) # 4 Hours
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
try:
    api.authenticate()
    logging.info("Kaggle Auth: SUCCESS")
except Exception as e:
    logging.error(f"Kaggle Auth Failed: {e}")

def download_audio(video_id):
    output = str(AUDIO_DIR / "audio.wav")
    # Clean up local storage
    for f in AUDIO_DIR.glob("*"): 
        try: os.remove(f)
        except: pass
    
    logging.info(f"Downloading audio for: {video_id}")
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
        logging.error("KAGGLE_DATASET variable is missing in Railway!")
        return False
    try:
        logging.info(f"Pushing {video_id} to Kaggle...")
        # This zips the audio folder and sends it to your Kaggle dataset
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
            logging.error("channels.json not found in repo!")
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
            # Check for the single newest video
            res = subprocess.run(["yt-dlp", "--get-id", "--playlist-end", "1", channel], capture_output=True, text=True)
            vid = res.stdout.strip()
            
            if vid and vid not in processed:
                logging.info(f"New video detected: {vid}")
                if download_audio(vid):
                    if upload(vid):
                        processed.append(vid)
                        with open(PROCESSED_FILE, "w") as f: 
                            json.dump(processed, f)
                        logging.info(f"Success! {vid} moved to Kaggle.")
        
        logging.info(f"Cycle complete. Sleeping for {POLL_INTERVAL}s.")
        time.sleep(POLL_INTERVAL)

    except Exception as e:
        logging.error(f"Main Loop Error: {e}")
        time.sleep(60)
