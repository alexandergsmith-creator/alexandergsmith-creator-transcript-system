import os
import json
import subprocess
import shutil
import time
from datetime import datetime
from kaggle.api.kaggle_api_extended import KaggleApi

# --- CONFIGURATION (RAILWAY ENVIRONMENT) ---
KAGGLE_USERNAME = os.getenv('KAGGLE_USERNAME')
KAGGLE_KEY = os.getenv('KAGGLE_KEY')
DATASET_ID = os.getenv('KAGGLE_DATASET', 'alexandergordonsmith/youtube-jobs')

# Files/Paths
CHANNELS_JSON = "channels.json"
ARCHIVE_FILE = "archive.txt"
FAILURE_LOG = "failed.txt"
SEGMENT_TIME = 600  # 10 minute chunks

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def setup_kaggle():
    if not KAGGLE_USERNAME or not KAGGLE_KEY:
        log("❌ CRITICAL: KAGGLE_USERNAME or KAGGLE_KEY missing in Railway Variables.")
        return None
    
    os.environ['KAGGLE_USERNAME'] = KAGGLE_USERNAME
    os.environ['KAGGLE_KEY'] = KAGGLE_KEY
    
    api = KaggleApi()
    try:
        api.authenticate()
        log(f"✅ Authenticated as {KAGGLE_USERNAME}")
        return api
    except Exception as e:
        log(f"❌ Kaggle Auth Failed: {e}")
        return None

def get_target_urls():
    if not os.path.exists(CHANNELS_JSON):
        log(f"❌ {CHANNELS_JSON} not found in repository.")
        return []
    
    try:
        with open(CHANNELS_JSON, "r") as f:
            channel_ids = json.load(f)
        
        targets = []
        for cid in channel_ids:
            # Full Unload: Main Videos + Shorts
            targets.append(f"https://www.youtube.com/channel/{cid}/videos")
            targets.append(f"https://www.youtube.com/channel/@{cid}/shorts")
        return targets
    except Exception as e:
        log(f"❌ JSON Parsing Error: {e}")
        return []

def harvest_video(url, api):
    log(f"🎯 Targeting: {url}")
    
    # yt-dlp config: Low bitrate to save Railway Disk (1GB Limit)
    download_cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "--download-archive", ARCHIVE_FILE,
        "--output", "temp_audio.%(ext)s",
        "--no-playlist",
        "--break-on-existing", 
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        url
    ]
    
    try:
        # 1. Download
        subprocess.run(download_cmd, check=True)
        if not os.path.exists("temp_audio.wav"):
            log("⏭️ Video skipped (already in archive).")
            return

        # 2. Slice
        log("🔪 Slicing for Parallel Whisper processing...")
        if os.path.exists("chunks"): shutil.rmtree("chunks")
        os.makedirs("chunks", exist_ok=True)
        
        slice_cmd = [
            "ffmpeg", "-i", "temp_audio.wav",
            "-f", "segment", "-segment_time", str(SEGMENT_TIME),
            "-c", "copy", "chunks/part_%03d.wav"
        ]
        subprocess.run(slice_cmd, check=True)

        # 3. Upload
        log(f"📤 Pushing to Kaggle Dataset: {DATASET_ID}")
        api.dataset_create_version(
            DATASET_ID, 
            f"Archive Sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
            dir_mode='zip'
        )
        log("✨ Harvest Successful.")

    except Exception as e:
        log(f"⚠️ Failed: {e}")
        with open(FAILURE_LOG, "a") as f:
            f.write(f"{url}\n")
    
    finally:
        # THE PURGE: Absolute Storage Safety
        if os.path.exists("temp_audio.wav"): os.remove("temp_audio.wav")
        if os.path.isdir("chunks"): shutil.rmtree("chunks")
        log("🧹 Storage wiped.")

def main():
    api = setup_kaggle()
    if not api: return

    targets = get_target_urls()
    if not targets: return

    # Primary Crawl
    for url in targets:
        harvest_video(url, api)

    # Cleanup: Retry the failed list one last time
    if os.path.exists(FAILURE_LOG):
        log("🔄 Retrying failed links...")
        with open(FAILURE_LOG, "r") as f:
            failed_urls = f.readlines()
        open(FAILURE_LOG, 'w').close() 
        for url in failed_urls:
            harvest_video(url.strip(), api)

if __name__ == "__main__":
    main()
