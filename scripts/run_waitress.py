import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from waitress import serve
from wsgi import app


if __name__ == "__main__":
    host = os.getenv("CRS_WAITRESS_HOST", "127.0.0.1")
    port = int(os.getenv("CRS_WAITRESS_PORT", "8080"))
    threads = int(os.getenv("CRS_WAITRESS_THREADS", "8"))
    serve(app, host=host, port=port, threads=max(2, threads))
