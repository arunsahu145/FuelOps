"""
Petrol Pump Finance Manager ERP — Main Application Entry Point
Starts the embedded FastAPI server in a background thread and launches the PySide6 desktop UI.
"""
import sys
import threading
import time
import uvicorn
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from config import API_HOST, API_PORT
from api.app import create_app
from ui.main_window import MainWindow

# ── 1. EMBEDDED FASTAPI SERVICE RUNNER ─────────────────────────────────────
fastapi_app = create_app()

class APIServerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.server = None

    def run(self):
        try:
            config = uvicorn.Config(
                app=fastapi_app,
                host=API_HOST,
                port=API_PORT,
                log_level="warning",  # Keep output clean
                loop="asyncio"
            )
            self.server = uvicorn.Server(config)
            self.server.run()
        except Exception as e:
            print(f"[FATAL] Embedded FastAPI server failed to start: {e}")


# ── 2. APP LAUNCHER ────────────────────────────────────────────────────────
def main():
    # Initialize PySide6 GUI Application (High-DPI scaling is automatic in PySide6 6.x)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Start the API server in a separate background daemon thread
    print("[INIT] Starting embedded FastAPI service thread...")
    api_thread = APIServerThread()
    api_thread.start()

    # Allow a quick brief pause for server initialization
    time.sleep(1.0)

    # Launch desktop main application window
    print("[INIT] Launching PySide6 desktop ERP interface...")
    window = MainWindow()
    window.show()

    # Run PySide6 event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
