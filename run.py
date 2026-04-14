#!/usr/bin/env python3
"""
Chief of Staff Hub App - Development Server Launcher

Usage:
    source .venv/bin/activate
    python run.py

Or directly:
    .venv/bin/python run.py
"""
import uvicorn
import webbrowser
import threading
import time
import sys
from pathlib import Path

PORT = 8001

def open_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{PORT}")

if __name__ == "__main__":
    # Add app directory to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    print("=" * 50)
    print("  Chief of Staff Hub")
    print(f"  http://localhost:{PORT}")
    print("=" * 50)
    
    # Open browser automatically
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        reload_dirs=["app"]
    )
