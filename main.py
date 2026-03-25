import subprocess
import os
import static_ffmpeg

def download_youtube_audio(video_url):
    # 1. Initialize static-ffmpeg to get the paths to the binaries
    # This ensures Railway knows where ffmpeg is hiding
    static_ffmpeg.add_paths()
    
    # 2. Define the output filename template
    output_template = "downloads/%(title)s.%(ext)s"
    
    # 3. Ensure the downloads directory exists
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # 4. The full dl_cmd list:
    dl_cmd = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "--no-check-certificate",
        "-x",                                # Extract audio
        "--audio-format", "wav",             # Convert to WAV
        "--audio-quality", "0",              # Best quality
        
        # Security & Bot Bypassing
        "--remote-components", "ejs:github",
        "--js-runtime", "node",
        "--extractor-args", "youtube:player_client=web,tv", 
        
        # Audio Selection
        "-f", "bestaudio/best",
        
        # Output location
        "-o", output_template,
        
        # THE FIX: Tell yt-dlp to use the static-ffmpeg we just initialized
        "--prefer-ffmpeg",
        
        video_url
    ]

    try:
        print(f"--- Starting Download: {video_url} ---")
        # Run the command
        result = subprocess.run(dl_cmd, check=True, capture_output=True, text=True)
        print("Success!")
        print(result.stdout)
        
        # List files to prove it downloaded
        print("Files in downloads folder:", os.listdir("downloads"))
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Download failed for {video_url}")
        print(e.stderr)

if __name__ == "__main__":
    target_url = "https://www.youtube.com/watch?v=JFtlf8RoPZY"
    download_youtube_audio(target_url)
