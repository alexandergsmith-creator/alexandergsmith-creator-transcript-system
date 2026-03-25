import subprocess
import os
import static_ffmpeg
import json
import time

def process_youtube_to_kaggle(target_url):
    static_ffmpeg.add_paths()
    download_dir = "downloads"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # 1. THE HARVEST (Optimized for high-quality audio)
    dl_cmd = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "--no-check-certificate",
        "-x", "--audio-format", "wav", "--audio-quality", "0",
        "--remote-components", "ejs:github",
        "--js-runtime", "node",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "--extractor-args", "youtube:player_client=web;player_skip=configs,web_embedded_client",
        "-f", "ba/b", # Best Audio / Best
        "--playlist-end", "2",
        "--download-archive", "archive.txt",
        "-o", f"{download_dir}/%(title)s.%(ext)s",
        target_url
    ]

    try:
        print(f"🚀 HARVESTING: {target_url}")
        subprocess.run(dl_cmd, check=True)

        # 2. KAGGLE SYNC (The "Done the Rest" logic)
        user = os.environ.get('KAGGLE_USERNAME')
        if not user:
            print("❌ STOP: Add KAGGLE_USERNAME to Railway Variables!")
            return

        dataset_id = f"{user}/youtube-audio-harvest"
        
        # Create metadata for Kaggle
        with open(os.path.join(download_dir, "dataset-metadata.json"), "w") as f:
            json.dump({"title": "YouTube Audio Harvest", "id": dataset_id, "licenses": [{"name": "CC0-1.0"}]}, f)

        print(f"📦 PUSHING TO KAGGLE: {dataset_id}")
        
        # Check if we create or version
        status = subprocess.run(["kaggle", "datasets", "status", dataset_id], capture_output=True, text=True)
        
        if "Ready" not in status.stdout:
            subprocess.run(["kaggle", "datasets", "create", "-p", download_dir, "--dir-mode", "zip"], check=True)
        else:
            subprocess.run(["kaggle", "datasets", "version", "-p", download_dir, "-m", "Auto-sync", "--dir-mode", "zip"], check=True)
        
        print("✨ SUCCESS: Files are in the Kaggle Brain.")

        # 3. CLEANUP (Keep Railway disk empty)
        for f in os.listdir(download_dir):
            os.remove(os.path.join(download_dir, f))

    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    # Once this works, you can put a Channel link here!
    target = "https://www.youtube.com/watch?v=JFtlf8RoPZY"
    process_youtube_to_kaggle(target)
