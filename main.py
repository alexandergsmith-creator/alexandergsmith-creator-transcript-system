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
                search_url = f"https://www.youtube.com/channel/{chan_id}/videos"
                print(f"--- [SCAN] CHECKING ID: {chan_id} ---", flush=True)
                
                # We add --javascript-delay and force the player client
                base_args = [
                    "--no-check-certificate", 
                    "--extractor-args", "youtube:player_client=web",
                    "--allow-unplayable-formats",
                    "--javascript-delay", "5"
                ]
                
                if COOKIES_FILE.exists():
                    base_args.extend(["--cookies", str(COOKIES_FILE)])

                # 1. Get Video ID
                id_cmd = ["yt-dlp"] + base_args + ["--flat-playlist", "--print", "id", "--playlist-items", "1", search_url]
                res = subprocess.run(id_cmd, capture_output=True, text=True)
                vid = res.stdout.strip().split('\n')[0]

                print(f"DEBUG: Found Video ID: '{vid}'", flush=True)

                if vid and len(vid) == 11:
                    if vid not in processed or os.getenv('FORCE_ALL') == 'True':
                        print(f"--- [NEW] FOUND: {vid}. DOWNLOADING... ---", flush=True)
                        output = str(AUDIO_DIR / "audio.wav")
                        
                        # 2. Download - added 'bestaudio' fallback to ensure it finds a stream
                        dl_cmd = ["yt-dlp"] + base_args + [
                            "-x", "--audio-format", "wav",
                            "-f", "bestaudio/ba/worst", # Tries best, then any audio, then worst
                            "-o", output, 
                            f"https://youtube.com/watch?v={vid}"
                        ]
                        
                        result = subprocess.run(dl_cmd)
                        
                        if result.returncode == 0:
                            print(f"--- [UPLOAD] PUSHING TO KAGGLE ---", flush=True)
                            api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {vid}", dir_mode='zip')
                            
                            if vid not in processed:
                                processed.append(vid)
                                with open(PROCESSED_FILE, "w") as f:
                                    json.dump(processed, f)
                            print(f"--- [SUCCESS] {vid} COMPLETE ---", flush=True)
                        else:
                            print(f"--- [ERROR] DOWNLOAD FAILED FOR {vid} ---", flush=True)
                else:
                    print(f"--- [SKIP] No valid ID found for {chan_id} ---", flush=True)
                
                time.sleep(random.randint(10, 20))

            print("--- [SLEEP] CYCLE FINISHED ---", flush=True)
            time.sleep(14400)
        except Exception as e:
            print(f"--- [LOOP ERROR] {e} ---", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    run_scout()
