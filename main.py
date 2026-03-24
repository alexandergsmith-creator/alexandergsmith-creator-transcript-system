#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
import random
from pathlib import Path

# --- [CREDENTIALS] ---
os.environ['KAGGLE_USERNAME'] = "alexandergordonsmith"
os.environ['KAGGLE_KEY'] = "153ff4001bd116d721e522e19255d204"

try:
    from kaggle.api.kaggle_api_extended import KaggleApi
    print("--- [BOOT] LIBRARIES LOADED ---", flush=True)
except Exception as e:
    print(f"--- [CRASH] IMPORT ERROR: {e} ---", flush=True)
    sys.exit(1)

# --- [CONFIG] ---
CHANNELS_FILE = Path("channels.json")
PROCESSED_FILE = Path("processed.json")
COOKIES_FILE = Path("cookies.txt")
AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)

def run_scout():
    api = KaggleApi()
    api.authenticate()
    print("--- [AUTH] SUCCESS ---", flush=True)

    while True:
        try:
            processed = []
            if PROCESSED_FILE.exists():
                with open(PROCESSED_FILE) as f:
                    processed = json.load(f)

            with open(CHANNELS_FILE) as f:
                channels = json.load(f)

            for channel in channels:
                print(f"--- [SCAN] CHECKING: {channel} ---", flush=True)
                
                # Base args for yt-dlp
                base_args = ["--no-check-certificate", "--extractor-args", "youtube:player_client=web", "--quiet", "--no-warnings"]
                if COOKIES_FILE.exists():
                    base_args.extend(["--cookies", str(COOKIES_FILE)])

                # Get Video ID - specifically looking for the latest video
                id_cmd = ["yt-dlp"] + base_args + ["--get-id", "--playlist-end", "1", f"{channel}/videos"]
                res = subprocess.run(id_cmd, capture_output=True, text=True)
                vid = res.stdout.strip()

                print(f"DEBUG: Found Video ID: '{vid}'", flush=True)

                if vid and (vid not in processed or os.getenv('FORCE_ALL') == 'True'):
                    print(f"--- [NEW] FOUND: {vid}. DOWNLOADING... ---", flush=True)
                    output = str(AUDIO_DIR / "audio.wav")
                    
                    dl_cmd = ["yt-dlp"] + base_args + [
                        "-x", "--audio-format", "wav",
                        "-f", "ba/worst", 
                        "-o", output, 
                        f"https://youtube.com/watch?v={vid}"
                    ]
                    
                    if subprocess.run(dl_cmd).returncode == 0:
                        print(f"--- [UPLOAD] PUSHING TO KAGGLE ---", flush=True)
                        api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {vid}", dir_mode='zip')
                        
                        if vid not in processed:
                            processed.append(vid)
                            with open(PROCESSED_FILE, "w") as f:
                                json.dump(processed, f)
                        print(f"--- [SUCCESS] {vid} COMPLETE ---", flush=True)
                else:
                    reason = "Already processed" if vid in processed else "No ID found"
                    print(f"--- [SKIP] {vid} ({reason}) ---", flush=True)
                
                time.sleep(random.randint(5, 10))

            print("--- [SLEEP] CYCLE FINISHED ---", flush=True)
            time.sleep(14400)
        except Exception as e:
            print(f"--- [LOOP ERROR] {e} ---", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    run_scout()
