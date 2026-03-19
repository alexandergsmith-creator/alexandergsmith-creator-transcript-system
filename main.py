#!/usr/bin/env python3
import json
import time
import logging
import subprocess
import os
import signal
from pathlib import Path
from tempfile import NamedTemporaryFile
from kaggle.api.kaggle_api_extended import KaggleApi

# ================= CONFIG =================
CHANNELS_FILE = Path("channels.json")
# Default to 1 hour (3600s) to stay within free trial limits
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3600"))
KAGGLE_DATASET = os.getenv("KAGGLE_DATASET") 

AUDIO_DIR = Path("audio")
QUEUE_FILE = Path("queue.json")
PROCESSED_FILE = Path("processed.json")

# ================= SETUP =================
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s"
)

# Initialize Kaggle API
api = KaggleApi()
try:
    api.authenticate()
    logging.info("Kaggle Auth: SUCCESS")
except Exception as e:
    logging.error(f"Kaggle Auth: FAILED - {e}")

STOP = False

def handle_shutdown(signum, frame):
    global STOP
    logging.info("Shutdown signal received. Wrapping up...")
    STOP = True

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# ================= HELPERS =================
def load_json(path):
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logging.warning(f"JSON Load Error ({path}): {e}")
        return []

def atomic_save(path, data):
    """Saves JSON safely to prevent file corruption during crashes."""
    try:
        with NamedTemporaryFile("w", delete=False, dir=".", suffix=".tmp") as tmp:
            json.dump(data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp.name, path)
    except Exception as e:
        logging.error(f"Atomic Save Failed: {e}")

def cleanup_audio():
    """Wipes the audio directory to keep Railway disk usage at 0."""
    for file in AUDIO_DIR.glob("*"):
        try:
            os.remove(file)
            logging.info(f"Cleaned up: {file.name}")
        except Exception as e:
            logging.error(f"Cleanup error: {e}")

def upload_to_kaggle(video_id):
    """Uploads the local 'audio' folder to Kaggle as a new dataset version."""
    if not KAGGLE_DATASET:
        logging.error("KAGGLE_DATASET env var is missing.")
        return False
    
    try:
        logging.info(f"Uploading {video_id} to Kaggle...")
        # dir_mode='zip' is essential for faster uploads and handling wav files
        api.dataset_create_version(
            str(AUDIO_DIR), 
            version_notes=f"New Audio: {video_id}",
            dir_mode='zip'
        )
        logging.info("Kaggle Upload: SUCCESS")
        return True
    except Exception as e:
        logging.error(f"Kaggle Upload: FAILED - {e}")
        return False

# ================= YT-DLP LOGIC =================
def get_latest_videos():
    channels = load_json(CHANNELS_FILE)
    found_ids = []
    for channel in channels:
        try:
            # Only check the latest 2 videos to save bandwidth/time
            cmd = ["yt-dlp", "--flat-playlist", "--playlist-end", "2", "-J", channel]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                entries = data.get("entries", [])
                found_ids.extend([e["id"] for e in entries if e.get("id")])
        except Exception as e:
            logging.error(f"Fetch Error ({channel}): {e}")
    return found_ids

def download_audio(video_id):
    """Downloads YouTube audio and converts it to a single wav file."""
    output_template = str(AUDIO_DIR / "audio.wav")
    cleanup_audio() # Ensure directory is empty before starting
    
    try:
        cmd = [
            "yt-dlp", "-x", "--audio-format", "wav", 
            "--max-filesize", "500M", # Safety cap for Railway disk
            "-o", output_template, 
            f"https://youtube.com/watch?v={video_id}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        return result.returncode == 0
    except Exception as e:
        logging.error(f"Download Error ({video_id}): {e}")
        return False

# ================= MAIN LOOP =================
processed_list = load_json(PROCESSED_FILE)
processed_set = set(processed_list)
queue_list = load_json(QUEUE_FILE)

logging.info("Scout Service Started.")

while not STOP:
    try:
        # 1. Sync Queue with YouTube
        logging.info("Checking channels...")
        latest_videos = get_latest_videos()
        
        new_additions = False
        for vid in latest_videos:
            if vid not in processed_set and vid not in queue_list:
                logging.info(f"Queuing new video: {vid}")
                queue_list.append(vid)
                new_additions = True
        
        if new_additions:
            atomic_save(QUEUE_FILE, queue_list)

        # 2. Process one item from queue
        if queue_list and not STOP:
            current_vid = queue_list[0]
            
            if download_audio(current_vid):
                if upload_to_kaggle(current_vid):
                    # Only move to processed if upload succeeded
                    processed_list.append(current_vid)
                    processed_set.add(current_vid)
                    queue_list.pop(0)
                    
                    atomic_save(PROCESSED_FILE, processed_list)
                    atomic_save(QUEUE_FILE, queue_list)
                else:
                    logging.warning("Upload failed. Will retry next cycle.")
            else:
                logging.error(f"Skipping {current_vid} due to download failure.")
                queue_list.pop(0) # Remove failed to prevent infinite loop
                atomic_save(QUEUE_FILE, queue_list)

        # 3. Final Cleanup
        cleanup_audio()

        # 4. Wait for next poll
        logging.info(f"Sleeping for {POLL_INTERVAL}s...")
        for _ in range(POLL_INTERVAL // 5):
            if STOP: break
            time.sleep(5)

    except Exception as e:
        logging.error(f"Global Loop Error: {e}")
        time.sleep(60)

logging.info("Service Stopped.")
