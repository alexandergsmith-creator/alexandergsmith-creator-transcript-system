import subprocess
import os

def download_youtube_audio(video_url):
    # 1. Define the output filename template
    output_template = "downloads/%(title)s.%(ext)s"
    
    # 2. Ensure the downloads directory exists
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # 3. The full dl_cmd list:
    # This version includes the fixes from your Railway logs
    dl_cmd = [
        "yt-dlp",
        "--cookies", "cookies.txt",         # Authentication
        "--no-check-certificate",            # SSL Bypass
        "-x",                                # Extract audio
        "--audio-format", "wav",             # Convert to WAV
        "--audio-quality", "0",              # Best quality
        
        # FIX 1: Allow yt-dlp to download the 'ejs' solver from GitHub (Required for Railway)
        "--remote-components", "ejs:github",
        
        # FIX 2: Explicitly use Node.js and tell it to use 'web' first for cookies
        "--js-runtime", "node",
        "--extractor-args", "youtube:player_client=web,tv", 
        
        # FIX 3: Fallback logic - try to get best audio, but don't crash if it's tricky
        "-f", "ba/b",
        
        "-o", output_template,
        video_url
    ]

    try:
        print(f"--- Starting Download: {video_url} ---")
        # subprocess.run executes the command
        result = subprocess.run(dl_cmd, check=True, capture_output=True, text=True)
        print("Success!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Download failed for {video_url}")
        # This will show the new log if it still fails
        print(e.stderr)

if __name__ == "__main__":
    # Your target video
    target_url = "https://www.youtube.com/watch?v=JFtlf8RoPZY"
    download_youtube_audio(target_url)
