import subprocess
import os
import static_ffmpeg
import json

def process_youtube_to_kaggle(target_url):
    # 1. Setup Environment
    static_ffmpeg.add_paths()
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # 2. Download from YouTube
    dl_cmd = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "--no-check-certificate",
        "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--remote-components", "ejs:github",
        "--js-runtime", "node",
        "--extractor-args", "youtube:player_client=web,tv", 
        "-f", "bestaudio/best",
        "--prefer-ffmpeg",
        "--playlist-end", "5", 
        "-o", "downloads/%(title)s.%(ext)s",
        target_url
    ]

    print(f"--- Harvesting Audio: {target_url} ---")
    subprocess.run(dl_cmd, check=True)

    # 3. Push to Kaggle
    # Create a simple metadata file Kaggle requires
    dataset_metadata = {
        "title": "YouTube Audio Harvest",
        "id": f"{os.environ.get('KAGGLE_USERNAME')}/youtube-audio-harvest",
        "licenses": [{"name": "CC0-1.0"}]
    }
    
    with open("downloads/dataset-metadata.json", "w") as f:
        json.dump(dataset_metadata, f)

    print("--- Pushing to Kaggle Dataset ---")
    # This command creates the dataset if it's new, or updates it if it exists
    # It uses the API credentials you set in Railway Variables
    try:
        # Check if dataset exists, if not, create it; otherwise, version it.
        status = subprocess.run(["kaggle", "datasets", "status", dataset_metadata["id"]], capture_output=True)
        
        if status.returncode != 0:
            subprocess.run(["kaggle", "datasets", "create", "-p", "downloads", "--dir-mode", "zip"], check=True)
        else:
            subprocess.run(["kaggle", "datasets", "version", "-p", "downloads", "-m", "New harvest", "--dir-mode", "zip"], check=True)
        
        print("Success! Audio is now available in Kaggle.")
    except Exception as e:
        print(f"Kaggle Push Error: {e}")

if __name__ == "__main__":
    # The "The Rest" part: Point this at a channel
    target = "https://www.youtube.com/watch?v=JFtlf8RoPZY"
    process_youtube_to_kaggle(target)
