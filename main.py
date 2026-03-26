import os
import json
import subprocess
import shutil
import time
import random
from datetime import datetime
from kaggle.api.kaggle_api_extended import KaggleApi

# --- CONFIGURATION ---
DATASET_ID = os.getenv('KAGGLE_DATASET', 'alexandergordonsmith/youtube-jobs')
# Check if TEST_MODE is "True" in Railway
TEST_MODE = os.getenv('TEST_MODE', 'False').lower() == 'true'

CHANNELS_JSON = "channels.json"
ARCHIVE_FILE = "archive.txt"
FAILURE_LOG = "failed.txt"
SEGMENT_TIME = 600 

# Limit logic based on Test Mode
MAX_VIDEOS = 1 if TEST_MODE else 5

def log(message):
    prefix = "[TEST MODE]" if TEST_MODE else "[PROD]"
    print(f"{prefix} [{datetime.now().strftime('%H:%M:%S')}] {message}")

def setup_kaggle():
    api = KaggleApi()
    try:
        api.authenticate()
        log("✅ Kaggle Authenticated.")
        return api
    except Exception as e:
        log(f"❌ Kaggle Auth Failed: {e}")
        return None

def harvest_video(url, api):
    log(f"🎯 Target: {url} (Limit: {MAX_VIDEOS})")
    
    download_cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "-f", "ba/b",
        "--download-archive", ARCHIVE_FILE,
        "--output", "temp_audio.%(ext)s",
        "--playlist-items", f"1-{MAX_VIDEOS}",
        "--break-on-existing",
        "--ignore-errors",
        "--no-warnings",
        "--extractor-args", "youtube:player_client=android,web",
        "--sleep-interval", "15",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]
    download_cmd.append(url)
    
    try:
        subprocess.run(download_cmd, check=True)
        if not os.path.exists("temp_audio.wav"):
            return

        os.makedirs("chunks", exist_ok=True)
        subprocess.run(["ffmpeg", "-i", "temp_audio.wav", "-f", "segment", "-segment_time", str(SEGMENT_TIME), "-c", "copy", "chunks/part_%03d.wav"], check=True)
        
        api.dataset_create_version(DATASET_ID, f"Archive: {datetime.now().strftime('%m-%d %H:%M')}", dir_mode='zip')
        log("✅ Success: Uploaded to Kaggle.")
        
    except Exception as e:
        log(f"⚠️ Failed: {e}")
        with open(FAILURE_LOG, "a") as f: f.write(f"{url}\n")
    finally:
        if os.path.exists("temp_audio.wav"): os.remove("temp_audio.wav")
        if os.path.isdir("chunks"): shutil.rmtree("chunks")

def main():
    if TEST_MODE:
        log("🚀 RUNNING IN TEST MODE: Only grabbing 1 video & 1 short per channel.")
    
    api = setup_kaggle()
    if api is None: return

    if not os.path.exists(CHANNELS_JSON):
        log("🛑 Error: channels.json missing.")
        return

    with open(CHANNELS_JSON, "r") as f:
        cids = json.load(f)
    
    random.shuffle(cids) 
    
    # In Test Mode, maybe only check the first 2 channels to save time/money
    active_cids = cids[:2] if TEST_MODE else cids

    for cid in active_cids:
        for mode in ["videos", "shorts"]:
            url = f"https://www.youtube.com/channel/{cid}/{mode}"
            harvest_video(url, api)

if __name__ == "__main__":
    main()
