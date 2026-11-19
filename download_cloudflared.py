"""
Скрипт для скачивания официального Cloudflare Tunnel (cloudflared.exe)
для запуска Telegram Mini App без сторонних предупреждений.
"""
import urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parent / "cloudflared.exe"
URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

def main():
    if DEST.exists():
        print(f"[OK] cloudflared.exe already exists: {DEST}")
        return

    print("Downloading cloudflared.exe from Cloudflare GitHub...")
    try:
        urllib.request.urlretrieve(URL, DEST)
        print(f"[DONE] Successfully downloaded: {DEST}")
        print("Run tunnel command:")
        print("  .\\cloudflared.exe tunnel --url http://localhost:8080")
    except Exception as e:
        print(f"[ERROR] Failed to download: {e}")

if __name__ == "__main__":
    main()
