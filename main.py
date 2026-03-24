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
                # Construct the direct URL for the channel's latest video
                search_url = f"https://www.youtube.com/channel/{chan_id}/videos"
                print(f"--- [SCAN] CHECKING ID: {chan_id} ---", flush=True)
                
                base_args = [
                    "--no-check-certificate", 
                    "--extractor-args", "youtube:player_client=web",
                    "--flat-playlist",
                    "--print", "id"
                ]
                
                if COOKIES_FILE.exists():
                    base_args.extend(["--cookies", str(COOKIES_FILE)])

                # We use --playlist-items 1 to just get the very top video
                id_cmd = ["yt-dlp"] + base_args + ["--playlist-items", "1", search_url]
                res = subprocess.run(id_cmd, capture_output=True, text=True)
                vid = res.stdout.strip().split('\n')[0] # Get only the first line

                print(f"DEBUG: Found Video ID: '{vid}'", flush=True)

                if vid and len(vid) < 15: # Valid YouTube IDs are 11 chars
                    if vid not in processed or os.getenv('FORCE_ALL') == 'True':
                        print(f"--- [NEW] FOUND: {vid}. DOWNLOADING... ---", flush=True)
                        output = str(AUDIO_DIR / "audio.wav")
                        
                        dl_cmd = ["yt-dlp", "--no-check-certificate", "--extractor-args", "youtube:player_client=web"]
                        if COOKIES_FILE.exists():
                            dl_cmd.extend(["--cookies", str(COOKIES_FILE)])
                        
                        dl_cmd.extend([
                            "-x", "--audio-format", "wav",
                            "-f", "ba/worst", "-o", output, 
                            f"https://youtube.com/watch?v={vid}"
                        ])
                        
                        if subprocess.run(dl_cmd).returncode == 0:
                            print(f"--- [UPLOAD] PUSHING TO KAGGLE ---", flush=True)
                            api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {vid}", dir_mode='zip')
                            
                            if vid not in processed:
                                processed.append(vid)
                                with open(PROCESSED_FILE, "w") as f:
                                    json.dump(processed, f)
                            print(f"--- [SUCCESS] {vid} COMPLETE ---", flush=True)
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
