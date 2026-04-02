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

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    # Add app directory to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    print("=" * 50)
    print("  Chief of Staff Hub")
    print("  http://localhost:8000")
    print("=" * 50)
    
    # Open browser automatically
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"]
    )
