#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
import random
from pathlib import Path

os.environ['KAGGLE_USERNAME'] = "alexandergordonsmith"
os.environ['KAGGLE_KEY'] = "153ff4001bd116d721e522e19255d204"

try:
    from kaggle.api.kaggle_api_extended import KaggleApi
    print("--- [BOOT] LIBRARIES LOADED ---", flush=True)
except Exception as e:
    print(f"--- [CRASH] IMPORT ERROR: {e} ---", flush=True)
    sys.exit(1)

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

            for chan_id in channels:
                # Direct Search is often more reliable than RSS for big channels
                search_query = f"https://www.youtube.com/channel/{chan_id}/videos"
                print(f"--- [SCAN] SEARCHING FOR: {chan_id} ---", flush=True)
                
                # Force the android/ios client even for the ID lookup
                id_cmd = [
                    "yt-dlp", "--get-id", "--playlist-end", "1",
                    "--extractor-args", "youtube:player_client=android,ios",
                    "--no-check-certificate", search_query
                ]
                
                if COOKIES_FILE.exists():
                    id_cmd.extend(["--cookies", str(COOKIES_FILE)])

                res = subprocess.run(id_cmd, capture_output=True, text=True)
                vid = res.stdout.strip().split('\n')[0]

                print(f"DEBUG: Found Video ID: '{vid}'", flush=True)

                if vid and len(vid) == 11:
                    if vid not in processed or os.getenv('FORCE_ALL') == 'True':
                        print(f"--- [NEW] FOUND: {vid}. DOWNLOADING... ---", flush=True)
                        output = str(AUDIO_DIR / "audio.wav")
                        
                        dl_cmd = [
                            "yt-dlp", "-x", "--audio-format", "wav",
                            "--no-check-certificate",
                            "--extractor-args", "youtube:player_client=android,ios", 
                            "-f", "ba/worst", "-o", output,
                            f"https://youtube.com/watch?v={vid}"
                        ]
                        
                        if COOKIES_FILE.exists():
                            dl_cmd.extend(["--cookies", str(COOKIES_FILE)])
                        
                        if subprocess.run(dl_cmd).returncode == 0:
                            print(f"--- [UPLOAD] PUSHING TO KAGGLE ---", flush=True)
                            api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {vid}", dir_mode='zip')
                            
                            if vid not in processed:
                                processed.append(vid)
                                with open(PROCESSED_FILE, "w") as f:
                                    json.dump(processed, f)
                            print(f"--- [SUCCESS] {vid} COMPLETE ---", flush=True)
                
                time.sleep(random.randint(10, 20))

            print("--- [SLEEP] CYCLE FINISHED ---", flush=True)
            time.sleep(14400)
        except Exception as e:
            print(f"--- [LOOP ERROR] {e} ---", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    run_scout()
