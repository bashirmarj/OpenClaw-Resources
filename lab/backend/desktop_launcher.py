import webview
import threading
import uvicorn
import os
import sys
import time
from lab_bridge import app

def run_backend():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == "__main__":
    # Start FastAPI in a background thread
    t = threading.Thread(target=run_backend, daemon=True)
    t.start()

    # Give the server a moment to start
    time.sleep(2)

    # Create native window
    print("Launching Vectis Lab Desktop App...")
    webview.create_window(
        'Vectis Validation Lab', 
        'http://127.0.0.1:8000',
        width=1400,
        height=900,
        background_color='#020617'
    )
    webview.start()
