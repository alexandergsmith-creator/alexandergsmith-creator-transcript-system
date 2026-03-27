import os
import json
import subprocess
from datetime import datetime
from kaggle.api.kaggle_api_extended import KaggleApi

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def main():
    # 1. Setup Kaggle (Essential for the final goal)
    api = KaggleApi()
    api.authenticate()
    log("✅ Kaggle Authenticated")

    # 2. Pick the most famous target (MrBeast) as the ultimate test
    # If we can get his channel, we can get anyone's.
    test_url = "https://www.youtube.com/@MrBeast/videos"
    log(f"🔎 Testing simple grab on: {test_url}")

    # 3. Bare-bones yt-dlp command. No mobile spoofing, no fancy args.
    # We are just asking for the most basic info.
    cmd = [
        "yt-dlp",
        "--get-id",            # Just get the ID, don't even download yet
        "--playlist-items", "1",
        "--quiet",
        test_url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            video_id = result.stdout.strip()
            log(f"✨ SUCCESS! Found Video ID: {video_id}")
            log("Conclusion: Simple requests are NOT blocked right now.")
        else:
            error_msg = result.stderr
            log("❌ FAILED: Still blocked.")
            if "Sign in" in error_msg:
                log("Reason: IP-level 'Bot Challenge' active.")
            else:
                log(f"Reason: {error_msg[:100]}...")

    except Exception as e:
        log(f"⚠️ Script Error: {e}")

if __name__ == "__main__":
    main()
