#!/usr/bin/env python3
import os
import json
import time
import logging
import subprocess
from pathlib import Path

# --- STEP 1: SILENCE THE KAGGLE ERRORS ---
# We set these BEFORE importing the kaggle library.
os.environ['KAGGLE_USERNAME'] = "alexandergordonsmith" # Your Username
os.environ['KAGGLE_KEY'] = "153ff4001bd116d721e522e19255d204" # Your Token Key
os.environ['KAGGLE_API_TOKEN'] = os.getenv('KAGGLE_API_TOKEN', 'KGAT_153ff4001bd116d721e522e19255d204')

# --- STEP 2: SETUP FFMPEG ---
try:
    from static_ffmpeg import add_paths
    add_paths()
    logging.info("Internal FFmpeg: READY")
except:
    pass

# --- STEP 3: DELAYED KAGGLE IMPORT ---
# This prevents the OSError you kept seeing.
import kaggle
from kaggle.api.kaggle_api_extended import KaggleApi

# ================= CONFIG =================
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "14400"))
KAGGLE_DATASET = "alexandergordonsmith/youtube-jobs"
AUDIO_DIR = Path("audio")
PROCESSED_FILE = Path("processed.json")
CHANNELS_FILE = Path("channels.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Initialize API
api = KaggleApi()
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
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0

def upload(video_id):
    try:
        logging.info(f"Uploading {video_id}...")
        api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {video_id}", dir_mode='zip')
        return True
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        return False

# ================= MAIN LOOP =================
logging.info("Scout Service Active.")

while True:
    try:
        if not CHANNELS_FILE.exists():
            logging.error("channels.json not found!")
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
                        logging.info("Kaggle Updated.")
        
        logging.info(f"Cycle complete. Sleeping {POLL_INTERVAL}s.")
        time.sleep(POLL_INTERVAL)
    except Exception as e:
        logging.error(f"Loop error: {e}")
        time.sleep(60)
