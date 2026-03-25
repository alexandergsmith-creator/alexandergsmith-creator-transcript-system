import subprocess
import os
import static_ffmpeg
import json

def process_youtube_to_kaggle(target_url):
    # 1. Initialize FFmpeg and Folders
    static_ffmpeg.add_paths()
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # 2. The Cleaned-Up Download Command
    dl_cmd = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "--no-check-certificate",
        "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--remote-components", "ejs:github",
        "--js-runtime", "node",
        
        # Mimic a real desktop browser
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "--extractor-args", "youtube:player_client=web;player_skip=configs,web_embedded_client",
        
        # Quality and Automation
        "-f", "bestaudio/best",
        "--playlist-end", "2", 
        "--download-archive", "archive.txt",
        "-o", "downloads/%(title)s.%(ext)s",
        
        target_url
    ]

    try:
        print(f"--- Starting Harvest: {target_url} ---")
        subprocess.run(dl_cmd, check=True)

        # 3. Kaggle API Push
        # Verify KAGGLE_USERNAME and KAGGLE_KEY are in Railway Variables!
        dataset_id = f"{os.environ.get('KAGGLE_USERNAME')}/youtube-audio-harvest"
        
        metadata = {
            "title": "YouTube Audio Harvest",
            "id": dataset_id,
            "licenses": [{"name": "CC0-1.0"}]
        }
        
        with open("downloads/dataset-metadata.json", "w") as f:
            json.dump(metadata, f)

        print(f"--- Pushing to Kaggle: {dataset_id} ---")
        
        # Check if dataset exists to decide between 'create' or 'version'
        status = subprocess.run(["kaggle", "datasets", "status", dataset_id], capture_output=True)
        
        if status.returncode != 0:
            subprocess.run(["kaggle", "datasets", "create", "-p", "downloads", "--dir-mode", "zip"], check=True)
        else:
            subprocess.run(["kaggle", "datasets", "version", "-p", "downloads", "-m", "New audio harvest", "--dir-mode", "zip"], check=True)
        
        print("🚀 SUCCESS: Files are now in Kaggle.")

        # 4. Clean up Railway disk space
        for file in os.listdir("downloads"):
            os.remove(os.path.join("downloads", file))

    except subprocess.CalledProcessError as e:
        print("❌ ERROR: YouTube blocked the session. Refresh cookies.txt and keep the YT tab open!")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    # Point this to a channel when you're ready for 'The Rest'
    target = "https://www.youtube.com/watch?v=JFtlf8RoPZY"
    process_youtube_to_kaggle(target)
