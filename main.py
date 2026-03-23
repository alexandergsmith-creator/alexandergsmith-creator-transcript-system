#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
import random
from pathlib import Path

print("--- [BOOT] SCRIPT IS RUNNING ---", flush=True)

os.environ['KAGGLE_USERNAME'] = "alexandergordonsmith"
os.environ['KAGGLE_KEY'] = "153ff4001bd116d721e522e19255d204"

try:
    print("--- [BOOT] LOADING LIBRARIES... ---", flush=True)
    from kaggle.api.kaggle_api_extended import KaggleApi
    print("--- [BOOT] LIBRARIES LOADED ---", flush=True)
except Exception as e:
    print(f"--- [CRASH] IMPORT ERROR: {e} ---", flush=True)
    sys.exit(1)

KAGGLE_DATASET = "alexandergordonsmith/youtube-jobs"
CHANNELS_FILE = Path("channels.json")
COOKIES_FILE = Path("cookies.txt")
AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)

def run_scout():
    print("--- [AUTH] CONNECTING TO KAGGLE ---", flush=True)
    api = KaggleApi()
    api.authenticate()
    print("--- [AUTH] SUCCESS ---", flush=True)

    while True:
        try:
            with open(CHANNELS_FILE) as f:
                channels = json.load(f)

            for channel in channels:
                print(f"--- [SCAN] CHECKING: {channel} ---", flush=True)
                
                # Using Cookies to get the ID
                id_cmd = ["yt-dlp", "--get-id", "--playlist-end", "1"]
                if COOKIES_FILE.exists():
                    id_cmd.extend(["--cookies", str(COOKIES_FILE)])
                
                id_cmd.append(channel)
                res = subprocess.run(id_cmd, capture_output=True, text=True)
                vid = res.stdout.strip()

                if vid:
                    print(f"--- [FORCE] DOWNLOADING: {vid} ---", flush=True)
                    output = str(AUDIO_DIR / "audio.wav")
                    for f in AUDIO_DIR.glob("*"):
                        try: os.remove(f)
                        except: pass

                    dl_cmd = [
                        "yt-dlp", "-x", "--audio-format", "wav", 
                        "--no-check-certificate", "--geo-bypass",
                        "-o", output
                    ]
                    if COOKIES_FILE.exists():
                        dl_cmd.extend(["--cookies", str(COOKIES_FILE)])
                    
                    dl_cmd.append(f"https://youtube.com/watch?v={vid}")
                    
                    if subprocess.run(dl_cmd).returncode == 0:
                        print(f"--- [UPLOAD] PUSHING {vid} TO KAGGLE ---", flush=True)
                        api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {vid}", dir_mode='zip')
                        print(f"--- [SUCCESS] {vid} COMPLETE ---", flush=True)
                else:
                    print(f"--- [ERROR] COULD NOT GET VIDEO ID. CHECK COOKIES. ---", flush=True)
                    print(f"DEBUG LOG: {res.stderr}", flush=True)
                
                time.sleep(random.randint(10, 20))

            print("--- [SLEEP] CYCLE FINISHED. WAITING 4 HOURS ---", flush=True)
            time.sleep(14400)

        except Exception as e:
            print(f"--- [LOOP ERROR] {e} ---", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    run_scout()
