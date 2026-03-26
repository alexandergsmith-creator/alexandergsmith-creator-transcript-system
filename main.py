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
TEST_MODE = os.getenv('TEST_MODE', 'False').lower() == 'true'

CHANNELS_JSON = "channels.json"
ARCHIVE_FILE = "archive.txt"
FAILURE_LOG = "failed.txt"
SEGMENT_TIME = 600  # 10-minute chunks
MAX_VIDEOS = 1 if TEST_MODE else 5

def log(message):
    tag = "🧪 [TEST]" if TEST_MODE else "🚀 [PROD]"
    print(f"{tag} [{datetime.now().strftime('%H:%M:%S')}] {message}")

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
    log(f"🎯 Target: {url}")
    
    if shutil.which("ffmpeg") is None:
        log("❌ CRITICAL: ffmpeg not found in environment!")
        return

    # yt-dlp: The Harvester
    download_cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "--download-archive", ARCHIVE_FILE,
        "--output", "temp_audio.%(ext)s",
        "--playlist-items", f"1-{MAX_VIDEOS}",
        "--break-on-existing",
        "--ignore-errors",
        "--no-warnings",
        "--extractor-args", "youtube:player_client=android,web",
        "--sleep-interval", "10",
        url
    ]
    
    try:
        # Run download
        subprocess.run(download_cmd, check=False)
        
        if not os.path.exists("temp_audio.wav"):
            log(f"ℹ️ No new content found for: {url}")
            return

        # Slicing Logic
        log("🔪 Slicing audio into chunks...")
        if os.path.exists("chunks"): shutil.rmtree("chunks")
        os.makedirs("chunks", exist_ok=True)
        
        subprocess.run([
            "ffmpeg", "-i", "temp_audio.wav", 
            "-f", "segment", "-segment_time", str(SEGMENT_TIME), 
            "-c", "copy", "chunks/part_%03d.wav"
        ], check=True)
        
        # Kaggle "Passport" Creation
        log("📤 Creating Metadata & Uploading...")
        metadata = {
            "id": DATASET_ID,
            "title": "YouTube Jobs Archive",
            "licenses": [{"name": "CC0-1.0"}]
        }
        with open("chunks/dataset-metadata.json", "w") as f:
            json.dump(metadata, f)

        # Push to Kaggle
        api.dataset_create_version(
            folder="chunks",
            version_notes=f"Auto-Harvest: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            dir_mode='zip'
        )
        log("✨ Success: Data synced to Kaggle.")
        
    except Exception as e:
        log(f"⚠️ Error during harvest: {e}")
        with open(FAILURE_LOG, "a") as f: 
            f.write(f"[{datetime.now()}] {url}: {str(e)}\n")
    finally:
        # Resource Cleanup
        if os.path.exists("temp_audio.wav"): os.remove("temp_audio.wav")
        if os.path.isdir("chunks"): shutil.rmtree("chunks")
        # Clean up any leftover temp files
        for f in os.listdir("."):
            if f.startswith("temp_audio"): os.remove(f)

def main():
    api = setup_kaggle()
    if api is None: return

    # --- THE PEEK: View the Archive in Logs ---
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "r") as f:
            lines = f.readlines()
            log(f"📜 Archive has {len(lines)} entries. Already processed IDs:")
            for line in lines[-5:]: # Show last 5 for brevity
                print(f"   > {line.strip()}")
    else:
        log("📜 Archive is empty (Fresh start).")

    if not os.path.exists(CHANNELS_JSON):
        log("🛑 Error: channels.json missing.")
        return

    with open(CHANNELS_JSON, "r") as f:
        cids = json.load(f)
    
    random.shuffle(cids)
    
    # Process everything in PROD, just 2 in TEST
    active_list = cids[:2] if TEST_MODE else cids

    for cid in active_list:
        for mode in ["videos", "shorts"]:
            harvest_video(f"https://www.youtube.com/channel/{cid}/{mode}", api)
            time.sleep(2)

if __name__ == "__main__":
    main()
