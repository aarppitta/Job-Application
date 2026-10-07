"""Vercel entry point: the whole FastAPI backend runs as one Python function.

vercel.json sends every /api/* request here; FastAPI still sees the original path (/api/jobs, …).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402,F401  (Vercel serves this ASGI app)
