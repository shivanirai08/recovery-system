# Exposing local FastAPI to public internet via HTTPS tunnel.

from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = BACKEND_DIR / ".tools"
CLOUDFLARED = TOOLS_DIR / "cloudflared"
CLOUDFLARED_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/"
    "cloudflared-linux-amd64"
)
PORT = int(os.getenv("PORT", "8000"))
URL_RE = re.compile(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com")


def ensure_cloudflared() -> Path:
    if CLOUDFLARED.exists():
        return CLOUDFLARED
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    print("Downloading cloudflared (one-time)...")
    urllib.request.urlretrieve(CLOUDFLARED_URL, CLOUDFLARED)
    CLOUDFLARED.chmod(CLOUDFLARED.stat().st_mode | stat.S_IEXEC)
    return CLOUDFLARED


def print_webhook_url(public_url: str) -> None:
    webhook_url = f"{public_url}/webhooks/razorpay"
    print()
    print("Paste this HTTPS URL in Razorpay Dashboard → Webhooks:")
    print(webhook_url)
    print()
    print("Events: payment.failed, payment_link.paid, payment_link.expired")
    print("Secret: same as WEBHOOK_SECRET in .env.local")
    print("Keep this process running while you test payments.")
    print()


def start_cloudflared() -> None:
    binary = ensure_cloudflared()
    process = subprocess.Popen(
        [str(binary), "tunnel", "--url", f"http://127.0.0.1:{PORT}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert process.stdout is not None
    public_url = None
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        match = URL_RE.search(line)
        if match and public_url is None:
            public_url = match.group(0)
            print_webhook_url(public_url)
    process.wait()


if __name__ == "__main__":
    try:
        print(f"Starting Cloudflare tunnel to http://127.0.0.1:{PORT}")
        start_cloudflared()
    except KeyboardInterrupt:
        sys.exit(0)
