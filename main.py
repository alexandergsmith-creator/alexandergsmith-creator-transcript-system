import subprocess
import os

def download_youtube_audio(video_url):
    # 1. Define the output filename template
    # This saves files into a 'downloads' folder with the video title
    output_template = "downloads/%(title)s.%(ext)s"
    
    # 2. Ensure the downloads directory exists in the Railway container
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # 3. The full dl_cmd list:
    # This is what Python sends to the terminal to talk to yt-dlp
    dl_cmd = [
        "yt-dlp",
        "--cookies", "cookies.txt",         # Proves you are a logged-in user
        "--no-check-certificate",            # Bypasses SSL trust issues on Linux
        "-x",                                # Extract audio only
        "--audio-format", "wav",             # Convert the result to WAV
        "--audio-quality", "0",              # Highest quality conversion (VBR 0)
        
        # FIX: Tell yt-dlp to use the Node.js runtime to solve YouTube's 'n' challenge
        "--js-runtime", "node", 
        
        # FIX: Use multiple clients to find the best available audio streams
        "--extractor-args", "youtube:player_client=ios,web,tv", 
        
        "-f", "bestaudio/best",              # Automatically pick the highest bitrate
        "-o", output_template,               # Set the output path and filename
        video_url
    ]

    try:
        print(f"--- Starting Download: {video_url} ---")
        # Run the command and wait for it to finish
        result = subprocess.run(dl_cmd, check=True, capture_output=True, text=True)
        print("Success!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Download failed for {video_url}")
        # This prints the specific error from yt-dlp so we can debug it
        print(e.stderr)

if __name__ == "__main__":
    # Target URL - you can change this to a channel link later
    target_url = "https://www.youtube.com/watch?v=JFtlf8RoPZY"
    download_youtube_audio(target_url)
