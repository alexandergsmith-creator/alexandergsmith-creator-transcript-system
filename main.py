import os
import json
import subprocess
import shutil
import time
import random
from datetime import datetime
from kaggle.api.kaggle_api_extended import KaggleApi

# --- CONFIGURATION ---
# Ensure these match your Railway Variables
DATASET_ID = os.getenv('KAGGLE_DATASET', 'alexandergordonsmith/youtube-jobs')
TEST_MODE = os.getenv('TEST_MODE', 'False').lower() == 'true'

CHANNELS_JSON = "channels.json"
ARCHIVE_FILE = "archive.txt"
FAILURE_LOG = "failed.txt"
SEGMENT_TIME = 600  # 10-minute chunks
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
    log(f"🎯 Target: {url}")
    
    # Pre-flight check for ffmpeg (Since we added it to nixpacks.toml)
    if shutil.which("ffmpeg") is None:
        log("❌ CRITICAL: ffmpeg not found. Check nixpacks.toml!")
        return

    # yt-dlp command with Android spoofing to bypass blocks
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
        result = subprocess.run(download_cmd, capture_output=True, text=True)
        
        if not os.path.exists("temp_audio.wav"):
            log(f"ℹ️ No new videos or already archived: {url}")
            return

        # --- SLICING PHASE ---
        log("🔪 Slicing into 10-minute chunks...")
        if os.path.exists("chunks"): shutil.rmtree("chunks")
        os.makedirs("chunks", exist_ok=True)
        
        subprocess.run([
            "ffmpeg", "-i", "temp_audio.wav", 
            "-f", "segment", 
            "-segment_time", str(SEGMENT_TIME), 
            "-c", "copy", 
            "chunks/part_%03d.wav"
        ], check=True)
        
        # --- KAGGLE UPLOAD PHASE ---
        log("📤 Preparing Kaggle Upload...")
        
        # Create the required dataset-metadata.json (The "Passport")
        # This fixes the 'Invalid Folder' error
        metadata = {
            "id": DATASET_ID,
            "title": "YouTube Jobs Archive",
            "licenses": [{"name": "CC0-1.0"}]
        }
        with open("chunks/dataset-metadata.json", "w") as f:
            json.dump(metadata, f)

        # Upload the entire 'chunks' folder
        api.dataset_create_version(
            folder="chunks",
            version_notes=f"Harvested: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            dir_mode='zip'
        )
        log("✨ Success: Uploaded to Kaggle.")
        
    except Exception as e:
        log(f"⚠️ Operation Failed: {e}")
        with open(FAILURE_LOG, "a") as f: f.write(f"{url} - {str(e)}\n")
    finally:
        # Cleanup to save Railway disk space
        if os.path.exists("temp_audio.wav"): os.remove("temp_audio.wav")
        if os.path.isdir("chunks"): shutil.rmtree("chunks")
        for f in os.listdir("."):
            if f.startswith("temp_audio"): os.remove(f)

def main():
    api = setup_kaggle()
    if api is None: return

    if not os.path.exists(CHANNELS_JSON):
        log("🛑 Error: channels.json missing.")
        return

    with open(CHANNELS_JSON, "r") as f:
        cids = json.load(f)
    
    # Shuffle so we don't always hit the same channel first
    random.shuffle(cids) 
    
    # In Test Mode, we only process 2 channels to verify the pipeline
    active_cids = cids[:2] if TEST_MODE else cids

    for cid in active_cids:
        for mode in ["videos", "shorts"]:
            url = f"https://www.youtube.com/channel/{cid}/{mode}"
            harvest_video(url, api)
            # Short rest between channels to stay under the radar
            time.sleep(5)

if __name__ == "__main__":
    main()
