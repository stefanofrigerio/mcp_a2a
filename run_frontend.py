#!/usr/bin/env python3
"""
Script per avviare il frontend web
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from frontend.web_app import app
import uvicorn

if __name__ == "__main__":
    print("🌐 Avvio frontend web su http://localhost:8000")
    print("📝 Apri il browser e vai su http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

