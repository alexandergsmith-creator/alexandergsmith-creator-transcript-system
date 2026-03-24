#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
import random
from pathlib import Path

# Kaggle Setup
os.environ['KAGGLE_USERNAME'] = "alexandergordonsmith"
os.environ['KAGGLE_KEY'] = "153ff4001bd116d721e522e19255d204"

try:
    from kaggle.api.kaggle_api_extended import KaggleApi
    print("--- [BOOT] HQ ENGINE ACTIVATED ---", flush=True)
except Exception as e:
    print(f"--- [CRASH] {e} ---", flush=True)
    sys.exit(1)

CHANNELS_FILE = Path("channels.json")
PROCESSED_FILE = Path("processed.json")
COOKIES_FILE = Path("cookies.txt")
AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)

def run_scout():
    api = KaggleApi()
    api.authenticate()

    while True:
        try:
            processed = json.load(open(PROCESSED_FILE)) if PROCESSED_FILE.exists() else []
            channels = json.load(open(CHANNELS_FILE))

            for chan_id in channels:
                # Target the uploads playlist directly
                upload_id = 'UU' + chan_id[2:] if chan_id.startswith('UC') else chan_id
                playlist_url = f"https://www.youtube.com/playlist?list={upload_id}"
                
                print(f"--- [SCAN] QUALITY CHECK: {chan_id} ---", flush=True)
                
                id_cmd = ["yt-dlp", "--get-id", "--flat-playlist", playlist_url]
                res = subprocess.run(id_cmd, capture_output=True, text=True)
                video_ids = res.stdout.strip().split('\n')

                for vid in video_ids:
                    if vid and len(vid) == 11 and vid not in processed:
                        print(f"--- [HQ DOWNLOAD] {vid} ---", flush=True)
                        output = str(AUDIO_DIR / f"{vid}.wav")
                        
                        # --- THE HQ BYPASS COMMAND ---
                        dl_cmd = [
                            "yt-dlp",
                            "-x", "--audio-format", "wav",
                            "--audio-quality", "0", 
                            "--no-check-certificate",
                            # 'tv' client doesn't use the 'n' challenge as much
                            # 'web_creator' gets us the highest bitrate possible
                            "--extractor-args", "youtube:player_client=tv,web_creator",
                            "-f", "bestaudio[ext=m4a]/bestaudio", # Prefer high-bitrate M4A/Opus
                            "-o", output,
                            f"https://youtube.com/watch?v={vid}"
                        ]
                        
                        if COOKIES_FILE.exists():
                            dl_cmd.extend(["--cookies", str(COOKIES_FILE)])
                        
                        result = subprocess.run(dl_cmd)
                        
                        if result.returncode == 0:
                            print(f"--- [KAGGLE] PUSHING HQ: {vid} ---", flush=True)
                            api.dataset_create_version(str(AUDIO_DIR), version_notes=f"HQ ID: {vid}", dir_mode='zip')
                            if os.path.exists(output): os.remove(output)
                            
                            processed.append(vid)
                            with open(PROCESSED_FILE, "w") as f: json.dump(processed, f)
                            time.sleep(random.randint(30, 60))
                        else:
                            print(f"--- [SKIP] CHALLENGE FAILED FOR {vid} ---", flush=True)
                
            time.sleep(14400)
        except Exception as e:
            print(f"--- [ERROR] {e} ---", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    run_scout()
