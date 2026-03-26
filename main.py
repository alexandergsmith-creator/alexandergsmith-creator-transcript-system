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
        log("❌ CRITICAL: ffmpeg not found!")
        return

    # THE POLISH: Using the iOS/TV client fallback + Node.js JS engine
    # This is the current 2026 "Gold Standard" for bypassing bot checks
    download_cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "--download-archive", ARCHIVE_FILE,
        "--output", "temp_audio.%(ext)s",
        "--playlist-items", f"1-{MAX_VIDEOS}",
        "--break-on-existing",
        "--ignore-errors",
        "--no-warnings",
        # Force the use of clients that don't trigger the "Sign In" block as easily
        "--extractor-args", "youtube:player_client=ios,tv;player_skip=webpage",
        # Use Node.js to solve the YouTube JS challenges (Requires node in nixpacks.toml)
        "--js-runtime", "node",
        "--sleep-interval", "15",
        url
    ]
    
    try:
        # Run download
        process = subprocess.run(download_cmd, capture_output=True, text=True)
        
        # Check if we got the "Sign in" error even with the fix
        if "Sign in to confirm you're not a bot" in process.stderr:
            log("⚠️ YouTube blocked the IP. Skipping to next target...")
            return

        if not os.path.exists("temp_audio.wav"):
            log(f"ℹ️ No new content or blocked: {url}")
            return

        # Slicing Logic
        log("🔪 Slicing audio...")
        if os.path.exists("chunks"): shutil.rmtree("chunks")
        os.makedirs("chunks", exist_ok=True)
        
        subprocess.run([
            "ffmpeg", "-i", "temp_audio.wav", 
            "-f", "segment", "-segment_time", str(SEGMENT_TIME), 
            "-c", "copy", "chunks/part_%03d.wav"
        ], check=True)
        
        # Kaggle Upload
        log("📤 Syncing to Kaggle...")
        metadata = {"id": DATASET_ID, "title": "YouTube Jobs Archive", "licenses": [{"name": "CC0-1.0"}]}
        with open("chunks/dataset-metadata.json", "w") as f:
            json.dump(metadata, f)

        api.dataset_create_version(
            folder="chunks",
            version_notes=f"Harvested: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            dir_mode='zip'
        )
        log("✨ Success: Data uploaded.")
        
    except Exception as e:
        log(f"⚠️ Error: {e}")
    finally:
        # Cleanup
        if os.path.exists("temp_audio.wav"): os.remove("temp_audio.wav")
        if os.path.isdir("chunks"): shutil.rmtree("chunks")
        for f in os.listdir("."):
            if f.startswith("temp_audio"): os.remove(f)

def main():
    api = setup_kaggle()
    if api is None: return

    # The Peek
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "r") as f:
            log(f"📜 Archive has {len(f.readlines())} entries.")
    
    if not os.path.exists(CHANNELS_JSON):
        log("🛑 Error: channels.json missing.")
        return

    with open(CHANNELS_JSON, "r") as f:
        cids = json.load(f)
    
    random.shuffle(cids)
    active_list = cids[:2] if TEST_MODE else cids

    for cid in active_list:
        # Polish: Validating the Channel ID format
        if not cid.startswith("UC"):
            log(f"⚠️ Skipping invalid ID: {cid} (Must start with UC)")
            continue
            
        for mode in ["videos", "shorts"]:
            harvest_video(f"https://www.youtube.com/channel/{cid}/{mode}", api)
            time.sleep(5)

if __name__ == "__main__":
    main()
