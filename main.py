import os
import json
import subprocess
import shutil
import time
import random
from datetime import datetime
from kaggle.api.kaggle_api_extended import KaggleApi

# --- CONFIGURATION ---
KAGGLE_USERNAME = os.getenv('KAGGLE_USERNAME')
KAGGLE_KEY = os.getenv('KAGGLE_KEY')
DATASET_ID = os.getenv('KAGGLE_DATASET', 'alexandergordonsmith/youtube-jobs')

CHANNELS_JSON = "channels.json"
ARCHIVE_FILE = "archive.txt"
FAILURE_LOG = "failed.txt"
SEGMENT_TIME = 600 

def log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def setup_kaggle():
    os.environ['KAGGLE_USERNAME'] = KAGGLE_USERNAME
    os.environ['KAGGLE_KEY'] = KAGGLE_KEY
    api = KaggleApi()
    try:
        api.authenticate()
        return api
    except: return None

def harvest_video(url, api):
    log(f"🎯 Targeting: {url}")
    
    # STEALTH COMMAND: No cookies (they are dead), just pure spoofing
    download_cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "--download-archive", ARCHIVE_FILE,
        "--output", "temp_audio.%(ext)s",
        "--no-playlist",
        "--break-on-existing",
        "--ignore-errors",
        "--no-warnings",
        "--add-header", "Accept-Language:en-US,en;q=0.9",
        "--extractor-args", "youtube:player_client=android,web", # Force specific clients
        "--sleep-interval", "30",        # Mandatory wait to cool the IP
        "--max-sleep-interval", "90",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]

    download_cmd.append(url)
    
    try:
        subprocess.run(download_cmd, check=True)
        if not os.path.exists("temp_audio.wav"):
            return

        # Slicing & Uploading
        os.makedirs("chunks", exist_ok=True)
        subprocess.run(["ffmpeg", "-i", "temp_audio.wav", "-f", "segment", "-segment_time", str(SEGMENT_TIME), "-c", "copy", "chunks/part_%03d.wav"], check=True)
        
        api.dataset_create_version(DATASET_ID, f"Archive: {datetime.now().strftime('%m-%d %H:%M')}", dir_mode='zip')
        log("✅ Success.")
        
    except Exception as e:
        log(f"❌ Blocked/Failed: {e}")
        with open(FAILURE_LOG, "a") as f: f.write(f"{url}\n")
    finally:
        if os.path.exists("temp_audio.wav"): os.remove("temp_audio.wav")
        if os.path.isdir("chunks"): shutil.rmtree("chunks")

def main():
    api = setup_kaggle()
    if not api or not os.path.exists(CHANNELS_JSON): return

    with open(CHANNELS_JSON, "r") as f:
        cids = json.load(f)
    
    # Shuffle to avoid hammering one specific channel
    random.shuffle(cids) 
    
    for cid in cids:
        # Check both videos and shorts, but shuffle them
        types = ["videos", "shorts"]
        random.shuffle(types)
        for t in types:
            url = f"https://www.youtube.com/channel/{cid}/{t}"
            harvest_video(url, api)

if __name__ == "__main__":
    main()
