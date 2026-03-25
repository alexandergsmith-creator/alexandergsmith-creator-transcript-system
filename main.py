import os
import subprocess
import time
import shutil
from kaggle.api.kaggle_api_extended import KaggleApi

# --- CONFIGURATION ---
# Path to your channels.txt (One URL per line)
CHANNELS_FILE = "channels.txt" 
# Memory of what we've already done
ARCHIVE_FILE = "archive.txt" 
# Where broken videos go to be retried last
FAILURE_LOG = "failed.txt"
# Segment length (10 minutes)
SEGMENT_TIME = 600 

def setup_kaggle():
    api = KaggleApi()
    api.authenticate()
    return api

def get_channels():
    if not os.path.exists(CHANNELS_FILE):
        return []
    with open(CHANNELS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def harvest_video(url, api):
    """Downloads, Slices, Uploads, and Purges ONE video."""
    print(f"🚀 Starting harvest: {url}")
    
    # 1. DOWNLOAD (Audio only, newest first, including shorts)
    # We use -f 139/140 for low-bitrate m4a to save Railway disk space
    download_cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "--download-archive", ARCHIVE_FILE,
        "--output", "temp_audio.%(ext)s",
        "--no-playlist", # Process one video at a time in the loop
        url
    ]
    
    try:
        result = subprocess.run(download_cmd, check=True)
        if not os.path.exists("temp_audio.wav"):
            print("⏭️ Video already in archive or skipped.")
            return

        # 2. SLICE (10-minute chunks for the 'Parallel Brain')
        print("🔪 Slicing into 10-minute chunks...")
        os.makedirs("chunks", exist_ok=True)
        slice_cmd = [
            "ffmpeg", "-i", "temp_audio.wav",
            "-f", "segment", "-segment_time", str(SEGMENT_TIME),
            "-c", "copy", "chunks/part_%03d.wav"
        ]
        subprocess.run(slice_cmd, check=True)

        # 3. UPLOAD TO KAGGLE
        print("📤 Pushing to Kaggle...")
        # Replace 'your-username/dataset-name' with yours
        api.dataset_create_version("your-username/youtube-archive", "Automated Harvest Update", dir_mode='zip')

        print("✅ Success!")

    except Exception as e:
        print(f"❌ Failed: {e}")
        with open(FAILURE_LOG, "a") as f:
            f.write(f"{url}\n")
    
    finally:
        # 4. PURGE (The 'One-In, One-Out' rule to save 1GB limit)
        if os.path.exists("temp_audio.wav"): os.remove("temp_audio.wav")
        if os.path.isdir("chunks"): shutil.rmtree("chunks")

def main():
    api = setup_kaggle()
    channels = get_channels()

    # PHASE 1: Fresh Harvest (Newest to Oldest)
    for channel in channels:
        print(f"📺 Processing Channel: {channel}")
        # This tells yt-dlp to give us the list of videos in the channel
        harvest_video(channel, api)

    # PHASE 2: The "Last Resort" (Retry Failures)
    if os.path.exists(FAILURE_LOG):
        print("🔄 Retrying failed videos...")
        with open(FAILURE_LOG, "r") as f:
            failed_urls = f.readlines()
        
        # Clear log before retrying
        open(FAILURE_LOG, 'w').close() 
        
        for url in failed_urls:
            harvest_video(url.strip(), api)

if __name__ == "__main__":
    main()
