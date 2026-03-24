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

def get_upload_playlist_id(chan_id):
    # YouTube channel IDs (UC...) can be turned into Upload Playlist IDs (UU...)
    # by simply changing the second letter from 'C' to 'U'
    if chan_id.startswith('UC'):
        return 'UU' + chan_id[2:]
    return chan_id

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
                upload_id = get_upload_playlist_id(chan_id)
                playlist_url = f"https://www.youtube.com/playlist?list={upload_id}"
                print(f"--- [DEEP SCAN] TARGETING ALL VIDEOS FOR: {chan_id} ---", flush=True)
                
                # We use --flat-playlist to get the IDs of EVERY video in the list
                # without downloading the full webpage for each one.
                id_cmd = [
                    "yt-dlp", "--get-id", "--flat-playlist",
                    "--extractor-args", "youtube:player_client=android,ios",
                    "--no-check-certificate", playlist_url
                ]
                
                if COOKIES_FILE.exists():
                    id_cmd.extend(["--cookies", str(COOKIES_FILE)])

                res = subprocess.run(id_cmd, capture_output=True, text=True)
                video_ids = res.stdout.strip().split('\n')

                print(f"DEBUG: Found {len(video_ids)} potential videos in playlist.", flush=True)

                for vid in video_ids:
                    if vid and len(vid) == 11 and vid not in processed:
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
                            print(f"--- [UPLOAD] PUSHING {vid} TO KAGGLE ---", flush=True)
                            api.dataset_create_version(str(AUDIO_DIR), version_notes=f"ID: {vid}", dir_mode='zip')
                            
                            processed.append(vid)
                            with open(PROCESSED_FILE, "w") as f:
                                json.dump(processed, f)
                            
                            # Wait between downloads to avoid getting IP banned
                            time.sleep(random.randint(30, 60))
                
                time.sleep(random.randint(60, 120))

            print("--- [CYCLE FINISHED] ALL CHANNELS PROCESSED ---", flush=True)
            time.sleep(14400)
        except Exception as e:
            print(f"--- [LOOP ERROR] {e} ---", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    run_scout()
