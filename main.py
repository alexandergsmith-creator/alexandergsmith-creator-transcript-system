#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
import random
import re
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
                # Use the RSS Feed URL - Much harder for YT to block
                rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={chan_id}"
                print(f"--- [SCAN] CHECKING RSS FOR: {chan_id} ---", flush=True)
                
                # Extract the first Video ID from the RSS feed using yt-dlp
                id_cmd = [
                    "yt-dlp", "--get-id", "--playlist-end", "1", 
                    "--no-check-certificate", rss_url
                ]
                res = subprocess.run(id_cmd, capture_output=True, text=True)
                vid = res.stdout.strip().split('\n')[0]

                print(f"DEBUG: Found Video ID: '{vid}'", flush=True)

                if vid and len(vid) == 11:
                    if vid not in processed or os.getenv('FORCE_ALL') == 'True':
                        print(f"--- [NEW] FOUND: {vid}. DOWNLOADING... ---", flush=True)
                        output = str(AUDIO_DIR / "audio.wav")
                        
                        # Use cookies and web player client for the actual download
                        dl_cmd = [
                            "yt-dlp", "-x", "--audio-format", "wav",
                            "--no-check-certificate",
                            "--extractor-args", "youtube:player_client=web",
                            "-f", "bestaudio/ba/worst",
                            "-o", output
                        ]
                        
                        if COOKIES_FILE.exists():
                            dl_cmd.extend(["--cookies", str(COOKIES_FILE)])
                        
                        dl_cmd.append(f"https://youtube.com/watch?v={vid}")
                        
                        if subprocess.run(dl_cmd).returncode == 0:
                            print(f"--- [UPLOAD] PUSHING TO KAGGLE ---", flush=True)
                            api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {vid}", dir_mode='zip')
                            
                            if vid not in processed:
                                processed.append(vid)
                                with open(PROCESSED_FILE, "w") as f:
                                    json.dump(processed, f)
                            print(f"--- [SUCCESS] {vid} COMPLETE ---", flush=True)
                else:
                    print(f"--- [SKIP] No ID found in RSS for {chan_id} ---", flush=True)
                
                time.sleep(random.randint(15, 30))

            print("--- [SLEEP] CYCLE FINISHED ---", flush=True)
            time.sleep(14400)
        except Exception as e:
            print(f"--- [LOOP ERROR] {e} ---", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    run_scout()
