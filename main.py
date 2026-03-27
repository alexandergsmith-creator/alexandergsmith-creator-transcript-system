import os
import json
import subprocess
import shutil
import random
from datetime import datetime
from kaggle.api.kaggle_api_extended import KaggleApi

# --- SIMPLE CONFIG ---
DATASET_ID = os.getenv('KAGGLE_DATASET', 'alexandergordonsmith/youtube-jobs')
CHANNELS_JSON = "channels.json"
ARCHIVE_FILE = "archive.txt"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def harvest_video(url, api):
    log(f"🎯 Target: {url}")
    
    # THE SIMPLEST DOWNLOAD COMMAND
    # No spoofing, just the basics that worked in our test
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
        subprocess.run(download_cmd, check=False)
        
        if not os.path.exists("temp.wav"):
            log("ℹ️ No new videos or skipped.")
            return

        # Slicing into 10-minute chunks
        log("🔪 Slicing...")
        if os.path.exists("chunks"): shutil.rmtree("chunks")
        os.makedirs("chunks", exist_ok=True)
        
        # Simple ffmpeg segmenting
        subprocess.run([
            "ffmpeg", "-i", "temp.wav", 
            "-f", "segment", "-segment_time", "600", 
            "-c", "copy", "chunks/%03d.wav"
        ], check=True)
        
        # Kaggle Upload
        log("📤 Syncing to Kaggle...")
        metadata = {"id": DATASET_ID, "title": "YouTube Jobs Archive", "licenses": [{"name": "CC0-1.0"}]}
        with open("chunks/dataset-metadata.json", "w") as f:
            json.dump(metadata, f)

        api.dataset_create_version(
            folder="chunks",
            version_notes=f"Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            dir_mode='zip'
        )
        log("✨ Success: Data uploaded.")
        
    except Exception as e:
        log(f"⚠️ Error: {e}")
    finally:
        # Cleanup
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
        cids = json.load(f)
    
    # Shuffle and pick ONE channel to keep the profile low
    random.shuffle(cids)
    target_id = cids[0]

    # Try both Videos and Shorts for this one channel
    for mode in ["videos", "shorts"]:
        # Use the @handle or the ID directly in the URL
        url = f"https://www.youtube.com/channel/{target_id}/{mode}"
        harvest_video(url, api)

if __name__ == "__main__":
    main()
