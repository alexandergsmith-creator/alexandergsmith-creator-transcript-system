#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
import random
from pathlib import Path

# --- [BOOT] IMMEDIATE LOGGING ---
print("--- [BOOT] SCRIPT IS RUNNING ---", flush=True)

# --- [CREDENTIALS] ---
os.environ['KAGGLE_USERNAME'] = "alexandergordonsmith"
os.environ['KAGGLE_KEY'] = "153ff4001bd116d721e522e19255d204"

# --- [IMPORTS] ---
try:
    print("--- [BOOT] LOADING LIBRARIES... ---", flush=True)
    from kaggle.api.kaggle_api_extended import KaggleApi
    print("--- [BOOT] LIBRARIES LOADED ---", flush=True)
except Exception as e:
    print(f"--- [CRASH] IMPORT ERROR: {e} ---", flush=True)
    sys.exit(1)

# --- [CONFIG] ---
KAGGLE_DATASET = "alexandergordonsmith/youtube-jobs"
CHANNELS_FILE = Path("channels.json")
PROCESSED_FILE = Path("processed.json")
AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)

def run_scout():
    print("--- [AUTH] CONNECTING TO KAGGLE ---", flush=True)
    api = KaggleApi()
    api.authenticate()
    print("--- [AUTH] SUCCESS ---", flush=True)

    while True:
        try:
            # 1. Check for the Manual Force Variable in Railway Settings
            force_all = os.getenv("FORCE_ALL", "False").lower() == "true"
            if force_all:
                print("--- [OVERRIDE] FORCE_ALL IS ENABLED: DOWNLOADING EVERYTHING ---", flush=True)

            if not CHANNELS_FILE.exists():
                print("--- [ERROR] channels.json MISSING ---", flush=True)
                time.sleep(60)
                continue

            with open(CHANNELS_FILE) as f:
                channels = json.load(f)

            processed = []
            if PROCESSED_FILE.exists():
                try:
                    with open(PROCESSED_FILE) as f:
                        processed = json.load(f)
                except: processed = []

            for channel in channels:
                print(f"--- [SCAN] CHECKING: {channel} ---", flush=True)
                
                # Fetch latest Video ID with a fake browser header
                res = subprocess.run([
                    "yt-dlp", "--get-id", "--playlist-end", "1", 
                    "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    channel
                ], capture_output=True, text=True)
                
                vid = res.stdout.strip()

                # LOGIC: Download if it's new OR if Force_All is enabled
                if vid and (vid not in processed or force_all):
                    if force_all:
                        print(f"--- [FORCE] DOWNLOADING: {vid} (Ignoring history) ---", flush=True)
                    else:
                        print(f"--- [NEW] FOUND: {vid}. DOWNLOADING... ---", flush=True)
                    
                    output = str(AUDIO_DIR / "audio.wav")
                    for f in AUDIO_DIR.glob("*"): 
                        try: os.remove(f)
                        except: pass

                    # BROWSER SPOOFING COMMAND
                    dl_cmd = [
                        "yt-dlp", 
                        "-x", "--audio-format", "wav", 
                        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                        "--no-check-certificate",
                        "--geo-bypass",
                        "-o", output, 
                        f"https://youtube.com/watch?v={vid}"
                    ]
                    
                    if subprocess.run(dl_cmd).returncode == 0:
                        print(f"--- [UPLOAD] PUSHING {vid} TO KAGGLE ---", flush=True)
                        api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {vid}", dir_mode='zip')
                        
                        # Only save to processed list if we aren't in force mode
                        if not force_all:
                            processed.append(vid)
                            with open(PROCESSED_FILE, "w") as f:
                                json.dump(processed, f)
                        
                        print(f"--- [SUCCESS] {vid} COMPLETE ---", flush=True)
                    
                    # Prevent YouTube from getting suspicious
                    delay = random.randint(20, 45)
                    print(f"Throttling: Waiting {delay}s...", flush=True)
                    time.sleep(delay)
                else:
                    print(f"--- [SKIP] {vid} ALREADY PROCESSED ---", flush=True)

            print("--- [SLEEP] CYCLE FINISHED. WAITING 4 HOURS ---", flush=True)
            time.sleep(14400)

        except Exception as e:
            print(f"--- [LOOP ERROR] {e} ---", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    run_scout()
