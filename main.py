#!/usr/bin/env python3
import os
import sys

# 1. IMMEDIATE HEARTBEAT (If you don't see this in 5 seconds, Railway is broken)
print("--- BOOTING SYSTEM: STAGE 1 SUCCESS ---", flush=True)

# 2. FORCE CREDENTIALS
os.environ['KAGGLE_USERNAME'] = "alexandergordonsmith"
os.environ['KAGGLE_KEY'] = "153ff4001bd116d721e522e19255d204"

import json
import time
import logging
import subprocess
from pathlib import Path

print("--- LIBRARIES LOADED: STAGE 2 SUCCESS ---", flush=True)

# 3. DELAYED KAGGLE IMPORT
try:
    import kaggle
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    print("--- KAGGLE AUTH: STAGE 3 SUCCESS ---", flush=True)
except Exception as e:
    print(f"KAGGLE FAIL: {e}", flush=True)
    api = None

# 4. CONFIG
KAGGLE_DATASET = "alexandergordonsmith/youtube-jobs"
CHANNELS_FILE = Path("channels.json")
PROCESSED_FILE = Path("processed.json")
AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)

print(f"--- MONITORING STARTING NOW ---", flush=True)

while True:
    try:
        if not CHANNELS_FILE.exists():
            print("ERROR: channels.json not found in GitHub!")
            time.sleep(60)
            continue

        with open(CHANNELS_FILE) as f:
            channels = json.load(f)

        for channel in channels:
            print(f"Checking channel: {channel}", flush=True)
            # Get latest video
            res = subprocess.run(["yt-dlp", "--get-id", "--playlist-end", "1", channel], capture_output=True, text=True)
            vid = res.stdout.strip()

            if vid:
                print(f"Latest Video ID: {vid}", flush=True)
                # (Download/Upload logic continues here...)
        
        print("Cycle finished. Sleeping...")
        time.sleep(14400)
    except Exception as e:
        print(f"LOOP ERROR: {e}")
        time.sleep(60)
