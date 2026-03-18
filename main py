#!/usr/bin/env python3
import json
import time
import logging
import subprocess
import os
import signal
from pathlib import Path
from tempfile import NamedTemporaryFile

# ================= CONFIG FILE =================
CHANNELS_FILE = Path("channels.json")

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "600"))

AUDIO_DIR = Path("audio")
QUEUE_FILE = Path("queue.json")
PROCESSED_FILE = Path("processed.json")

# ================= SETUP =================
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

STOP = False

def handle_shutdown(signum, frame):
    global STOP
    logging.info("Shutdown signal received")
    STOP = True

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# ================= FILE HELPERS =================
def load_json(path):
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to read {path}: {e}")
        return []

def atomic_save(path, data):
    with NamedTemporaryFile("w", delete=False, dir=".") as tmp:
        json.dump(data, tmp, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
    os.replace(tmp.name, path)

# ================= LOAD CHANNELS =================
def load_channels():
    channels = load_json(CHANNELS_FILE)
    if not isinstance(channels, list):
        logging.error("channels.json must be a list")
        return []
    return channels

# ================= YT-DLP =================
def get_videos():
    channels = load_channels()
    all_videos = []

    for channel in channels:
        try:
            result = subprocess.run(
                ["yt-dlp", "--flat-playlist", "-J", channel],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                logging.error(f"yt-dlp failed for {channel}")
                continue

            data = json.loads(result.stdout)
            entries = data.get("entries", [])

            if not isinstance(entries, list):
                logging.error(f"Invalid response for {channel}")
                continue

            vids = [e["id"] for e in entries if "id" in e]
            all_videos.extend(vids)

        except Exception as e:
            logging.error(f"Error with {channel}: {e}")

    return all_videos

def download_audio(video_id):
    output = str(AUDIO_DIR / f"{video_id}.%(ext)s")

    if any(AUDIO_DIR.glob(f"{video_id}.*")):
        logging.info(f"{video_id} already downloaded")
        return True

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "-x",
                "--audio-format", "wav",
                "-o", output,
                f"https://youtube.com/watch?v={video_id}"
            ],
            capture_output=True,
            text=True,
            timeout=3600
        )

        if result.returncode != 0:
            logging.error(f"Download failed: {video_id}")
            return False

        logging.info(f"Downloaded {video_id}")
        return True

    except Exception as e:
        logging.error(f"Download error {video_id}: {e}")
        return False

# ================= MAIN =================
queue_list = load_json(QUEUE_FILE)
queue_set = set(queue_list)

processed_list = load_json(PROCESSED_FILE)
processed_set = set(processed_list)

backoff = 0

while not STOP:
    try:
        logging.info("Checking for new videos...")

        videos = get_videos()

        for vid in videos:
            if vid not in processed_set and vid not in queue_set:
                logging.info(f"New video: {vid}")
                queue_list.append(vid)
                queue_set.add(vid)

        atomic_save(QUEUE_FILE, queue_list)

        if queue_list:
            vid = queue_list.pop(0)
            queue_set.remove(vid)

            atomic_save(QUEUE_FILE, queue_list)

            success = download_audio(vid)

            if success:
                processed_list.append(vid)
                processed_set.add(vid)
                atomic_save(PROCESSED_FILE, processed_list)
            else:
                logging.warning(f"Retry later: {vid}")
                queue_list.append(vid)
                queue_set.add(vid)
                atomic_save(QUEUE_FILE, queue_list)
                time.sleep(30)

        backoff = 0

        for _ in range(POLL_INTERVAL // 5):
            if STOP:
                break
            time.sleep(5)

    except Exception as e:
        logging.error(f"Main loop error: {e}")

        backoff = min(3600, backoff * 2 + 5)
        logging.info(f"Backing off {backoff}s")

        time.sleep(backoff)

logging.info("Saving before exit...")
atomic_save(QUEUE_FILE, queue_list)
atomic_save(PROCESSED_FILE, processed_list)

logging.info("Exited cleanly")
