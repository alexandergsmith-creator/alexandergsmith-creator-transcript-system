import os
import json
import subprocess
import shutil
import time
from datetime import datetime
from kaggle.api.kaggle_api_extended import KaggleApi

# --- CONFIGURATION ---
KAGGLE_USERNAME = os.getenv('KAGGLE_USERNAME')
KAGGLE_KEY = os.getenv('KAGGLE_KEY')
DATASET_ID = os.getenv('KAGGLE_DATASET', 'alexandergordonsmith/youtube-jobs')

CHANNELS_JSON = "channels.json"
COOKIES_FILE = "cookies.txt" 
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
    except:
        return None

def harvest_video(url, api):
    log(f"🎯 Targeting: {url}")
    
    # THE HARDENED COMMAND
    download_cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "--download-archive", ARCHIVE_FILE,
        "--output", "temp_audio.%(ext)s",
        "--no-playlist",
        "--break-on-existing",
        "--ignore-errors",
        "--sleep-interval", "25",       # SLOW DOWN to avoid the 429 ban
        "--max-sleep-interval", "75", 
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]

    # Only attach if you've uploaded that cookies.txt we talked about
    if os.path.exists(COOKIES_FILE):
        download_cmd.extend(["--cookies", COOKIES_FILE])
        log("🍪 Cookies loaded.")
    
    download_cmd.append(url)
    
    try:
        subprocess.run(download_cmd, check=True)
        if not os.path.exists("temp_audio.wav"):
            return

        # Slicing & Kaggle Push
        log("🔪 Slicing...")
        os.makedirs("chunks", exist_ok=True)
        subprocess.run(["ffmpeg", "-i", "temp_audio.wav", "-f", "segment", "-segment_time", str(SEGMENT_TIME), "-c", "copy", "chunks/part_%03d.wav"], check=True)
        
        log(f"📤 Uploading to {DATASET_ID}...")
        api.dataset_create_version(DATASET_ID, f"Harvest: {datetime.now().strftime('%m-%d %H:%M')}", dir_mode='zip')
        log("✅ Success.")
        
    except Exception as e:
        log(f"❌ Failed: {e}")
        with open(FAILURE_LOG, "a") as f: f.write(f"{url}\n")
    finally:
        if os.path.exists("temp_audio.wav"): os.remove("temp_audio.wav")
        if os.path.isdir("chunks"): shutil.rmtree("chunks")
        log("🧹 Purged.")

def main():
    api = setup_kaggle()
    if not api: 
        log("❌ Kaggle Auth Failed.")
        return
    
    if not os.path.exists(CHANNELS_JSON):
        log("❌ No channels.json found.")
        return

    with open(CHANNELS_JSON, "r") as f:
        cids = json.load(f)
    
    for cid in cids:
        # Full Unload (Videos + Shorts)
        harvest_video(f"https://www.youtube.com/channel/{cid}/videos", api)
        harvest_video(f"https://www.youtube.com/channel/{cid}/shorts", api)

if __name__ == "__main__":
    main()
