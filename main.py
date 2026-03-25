import subprocess
import os

def download_youtube_audio(video_url):
    # 1. Define the output filename
    # %(title)s will be replaced by the actual video title
    output_template = "downloads/%(title)s.%(ext)s"
    
    # 2. Ensure the downloads directory exists
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # 3. The dl_cmd: These are the exact flags that worked in your terminal
    dl_cmd = [
        "yt-dlp",
        "--cookies", "cookies.txt",         # Uses your exported login session
        "--no-check-certificate",            # Bypasses the SSL trust issue
        "--prefer-free-formats",
        "-x",                                # Extract audio only
        "--audio-format", "wav",             # Convert specifically to WAV
        "--audio-quality", "0",              # 0 = highest quality conversion
        "--extractor-args", "youtube:player_client=web,tv", # Force trusted clients
        "-f", "bestaudio/best",              # Pick the best from the list we saw
        "-o", output_template,               # Save to the downloads folder
        video_url
    ]

    try:
        print(f"--- Starting Download: {video_url} ---")
        # subprocess.run executes the command just like you did in the terminal
        result = subprocess.run(dl_cmd, check=True, capture_output=True, text=True)
        print("Success!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Download failed for {video_url}")
        print(e.stderr)

# Example Usage:
if __name__ == "__main__":
    # You can replace this with your target URL or a list of URLs
    test_url = "https://www.youtube.com/watch?v=JFtlf8RoPZY"
    download_youtube_audio(test_url)
