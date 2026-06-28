from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
removed = 0
for path in ROOT.rglob("__pycache__"):
    shutil.rmtree(path, ignore_errors=True)
    removed += 1
for path in ROOT.rglob("*.pyc"):
    try:
        path.unlink()
        removed += 1
    except FileNotFoundError:
        pass
print(f"Cleared Python cache items: {removed}")
