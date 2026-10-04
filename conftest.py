import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

for folder in [ROOT, ROOT / "rag", ROOT / "ingestion", ROOT / "extraction", ROOT / "analysis", ROOT / "database", ROOT / "frontend"]:
    path = str(folder)
    if path not in sys.path:
        sys.path.insert(0, path)
