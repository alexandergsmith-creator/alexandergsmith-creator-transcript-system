import os
import subprocess
import shutil
import time
from kaggle.api.kaggle_api_extended import KaggleApi

# --- CONFIGURATION FROM RAILWAY VARIABLES ---
# Make sure these are set in your Railway 'Variables' tab!
KAGGLE_USERNAME = os.getenv('KAGGLE_USERNAME')
KAGGLE_KEY = os.getenv('KAGGLE_KEY')
DATASET_ID = os.getenv('KAGGLE_DATASET', 'alexandergordonsmith/youtube-jobs')

# Internal tracking files
CHANNELS_FILE = "channels.txt"
ARCHIVE_FILE = "archive.txt"
FAILURE_LOG = "failed.txt"
SEGMENT_TIME = 600  # 10 minute chunks

def setup_kaggle():
    """Authenticates using Railway Environment Variables."""
    if not KAGGLE_USERNAME or not KAGGLE_KEY:
        print("❌ Error: KAGGLE_USERNAME or KAGGLE_KEY not found in Railway Variables!")
        return None
    
    # Kaggle library looks for these specific environment variables
    os.environ['KAGGLE_USERNAME'] = KAGGLE_USERNAME
    os.environ['KAGGLE_KEY'] = KAGGLE_KEY
    
    api = KaggleApi()
    try:
        api.authenticate()
        print(f"✅ Authenticated as {KAGGLE_USERNAME}")
        return api
    except Exception as e:
        print(f"❌ Kaggle Auth Failed: {e}")
        return None

def harvest_video(url, api):
    """Processes one video: Download -> Slice -> Upload -> Delete."""
    print(f"\n--- Processing: {url} ---")
    
    # 1. DOWNLOAD (Audio only, newest first, including shorts)
    # We use low-bitrate to save Railway disk space and credits
    download_cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "--download-archive", ARCHIVE_FILE,
        "--output", "temp_audio.%(ext)s",
        "--no-playlist",
        url
    ]
    
    try:
        subprocess.run(download_cmd, check=True)
        if not os.path.exists("temp_audio.wav"):
            print("⏭️ Video already archived or skipped.")
            return

        # 2. SLICE (10-minute segments for parallel processing)
        print("🔪 Slicing audio...")
        os.makedirs("chunks", exist_ok=True)
        slice_cmd = [
            "ffmpeg", "-i", "temp_audio.wav",
            "-f", "segment", "-segment_time", str(SEGMENT_TIME),
            "-c", "copy", "chunks/part_%03d.wav"
        ]
        subprocess.run(slice_cmd, check=True)

        # 3. UPLOAD TO KAGGLE
        print(f"📤 Uploading chunks to {DATASET_ID}...")
        api.dataset_create_version(
            DATASET_ID, 
            f"Automated Update: {time.strftime('%Y-%m-%d %H:%M:%S')}", 
            dir_mode='zip'
        )
        print("✅ Upload Successful!")

    except Exception as e:
        print(f"⚠️ Failed to process {url}: {e}")
        with open(FAILURE_LOG, "a") as f:
            f.write(f"{url}\n")
    
    finally:
        # 4. PURGE (The 'One-In, One-Out' rule to stay under 1GB)
        if os.path.exists("temp_audio.wav"):
            os.remove("temp_audio.wav")
        if os.path.isdir("chunks"):
            shutil.rmtree("chunks")
        print("🧹 Cleaned up Railway storage.")

def main():
    api = setup_kaggle()
    if not api:
        return

    # Load your 50 channels from the file in your repo
    if not os.path.exists(CHANNELS_FILE):
        print(f"❌ {CHANNELS_FILE} not found! Create it in your repo.")
        return

    with open(CHANNELS_FILE, "r") as f:
        channels = [line.strip() for line in f if line.strip()]

    # PHASE 1: Full Unload (Newest to Oldest)
    for channel_url in channels:
        print(f"\n📺 Entering Channel: {channel_url}")
        # Passing the channel URL to harvest_video will trigger newest-first logic
        harvest_video(channel_url, api)

    # PHASE 2: Retry Failures
    if os.path.exists(FAILURE_LOG):
        print("\n🔄 Retrying failed videos...")
        with open(FAILURE_LOG, "r") as f:
            failed_urls = f.readlines()
        
        # Clear log for this run
        open(FAILURE_LOG, 'w').close() 
        
        for url in failed_urls:
            harvest_video(url.strip(), api)

if __name__ == "__main__":
    main()
