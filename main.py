#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
from pathlib import Path

# --- STEP 1: TALK IMMEDIATELY ---
# This forces Railway to show us the script is actually alive.
print("--- [BOOT] SCRIPT IS RUNNING ---", flush=True)

# --- STEP 2: SET CREDENTIALS ---
# Hardcoded to bypass any environment variable syncing delays.
os.environ['KAGGLE_USERNAME'] = "alexandergordonsmith"
os.environ['KAGGLE_KEY'] = "153ff4001bd116d721e522e19255d204"
print("--- [BOOT] KAGGLE CREDENTIALS SET ---", flush=True)

# --- STEP 3: PROTECTED IMPORTS ---
try:
    print("--- [BOOT] LOADING KAGGLE LIBRARIES... ---", flush=True)
    from kaggle.api.kaggle_api_extended import KaggleApi
    print("--- [BOOT] LIBRARIES LOADED SUCCESSFULLY ---", flush=True)
except Exception as e:
    print(f"--- [CRASH] IMPORT ERROR: {e} ---", flush=True)
    sys.exit(1)

# --- CONFIG ---
KAGGLE_DATASET = "alexandergordonsmith/youtube-jobs"
CHANNELS_FILE = Path("channels.json")
PROCESSED_FILE = Path("processed.json")
AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)

def run_scout():
    print("--- [AUTH] AUTHENTICATING WITH KAGGLE ---", flush=True)
    api = KaggleApi()
    api.authenticate()
    print("--- [AUTH] SUCCESS ---", flush=True)

    while True:
        try:
            if not CHANNELS_FILE.exists():
                print("--- [ERROR] channels.json NOT FOUND ---", flush=True)
                time.sleep(60)
                continue

            with open(CHANNELS_FILE) as f:
                channels = json.load(f)

            processed = []
            if PROCESSED_FILE.exists():
                with open(PROCESSED_FILE) as f:
                    processed = json.load(f)

            for channel in channels:
                print(f"--- [SCAN] CHECKING: {channel} ---", flush=True)
                # Get latest video ID
                res = subprocess.run(["yt-dlp", "--get-id", "--playlist-end", "1", channel], capture_output=True, text=True)
                vid = res.stdout.strip()

                if vid and vid not in processed:
                    print(f"--- [NEW] FOUND VIDEO: {vid}. STARTING DOWNLOAD... ---", flush=True)
                    
                    output = str(AUDIO_DIR / "audio.wav")
                    # Clean old files
                    for f in AUDIO_DIR.glob("*"): os.remove(f)

                    # Download
                    dl_cmd = ["yt-dlp", "-x", "--audio-format", "wav", "-o", output, f"https://youtube.com/watch?v={vid}"]
                    if subprocess.run(dl_cmd).returncode == 0:
                        print(f"--- [UPLOAD] PUSHING {vid} TO KAGGLE ---", flush=True)
                        api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {vid}", dir_mode='zip')
                        
                        processed.append(vid)
                        with open(PROCESSED_FILE, "w") as f:
                            json.dump(processed, f)
                        print(f"--- [SUCCESS] {vid} COMPLETE ---", flush=True)
                else:
                    print(f"--- [SKIP] {vid} ALREADY PROCESSED ---", flush=True)

            print("--- [SLEEP] CYCLE FINISHED. WAITING 4 HOURS ---", flush=True)
            time.sleep(14400)

        except Exception as e:
            print(f"--- [LOOP ERROR] {e} ---", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    run_scout()
