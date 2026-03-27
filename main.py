import os
import json
import subprocess
import shutil
import random
from datetime import datetime
from kaggle.api.kaggle_api_extended import KaggleApi

# --- CONFIG ---
DATASET_ID = os.getenv('KAGGLE_DATASET', 'alexandergordonsmith/youtube-jobs')
CHANNELS_JSON = "channels.json"
ARCHIVE_FILE = "archive.txt"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def harvest_video(url, api):
    log(f"🎯 Target: {url}")
    
    # SIMPLEST COMMAND: This proved to work in our 10:58 AM test
    download_cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "--download-archive", ARCHIVE_FILE,
        "--output", "temp.wav",
        "--playlist-items", "1",
        "--quiet", "--no-warnings",
        url
    ]
    
    try:
        # Run download
        subprocess.run(download_cmd, check=False)
        
        if not os.path.exists("temp.wav"):
            # If it's not there, it's either already archived or blocked
            log("ℹ️ No new videos or skipped (check archive.txt).")
            return

        # Slicing
        log("🔪 Slicing...")
        if os.path.exists("chunks"): shutil.rmtree("chunks")
        os.makedirs("chunks", exist_ok=True)
        subprocess.run(["ffmpeg", "-i", "temp.wav", "-f", "segment", "-segment_time", "600", "-c", "copy", "chunks/%03d.wav"], check=True)
        
        # Kaggle Meta
        with open("chunks/dataset-metadata.json", "w") as f:
            json.dump({"id": DATASET_ID, "title": "YouTube Archive", "licenses": [{"name": "CC0-1.0"}]}, f)

        # Push to Kaggle
        api.dataset_create_version("chunks", f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}", dir_mode='zip')
        log("✨ Success!")
        
    except Exception as e:
        log(f"⚠️ Error: {e}")
    finally:
        if os.path.exists("temp.wav"): os.remove("temp.wav")
        if os.path.isdir("chunks"): shutil.rmtree("chunks")

def main():
    api = KaggleApi()
    api.authenticate()
    log("✅ Kaggle Authenticated.")

    if not os.path.exists(CHANNELS_JSON):
        log("🛑 Error: channels.json missing.")
        return

    with open(CHANNELS_JSON, "r") as f:
        handles = json.load(f)
    
    # Pick ONE handle to keep it low-profile
    random.shuffle(handles)
    target = handles[0]

    # Process Videos and Shorts using the handle URL format
    for mode in ["videos", "shorts"]:
        # Handle format: https://www.youtube.com/@handle/videos
        # If your list still has UC IDs, this logic still works for them!
        base_url = f"https://www.youtube.com/{target}" if target.startswith('@') else f"https://www.youtube.com/channel/{target}"
        harvest_video(f"{base_url}/{mode}", api)

if __name__ == "__main__":
    main()
