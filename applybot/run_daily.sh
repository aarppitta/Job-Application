#!/bin/bash
# Daily auto-apply (for Hermes or a scheduler): log in with ~/.job-automation/config.json, really apply, print a summary.
cd "$(dirname "$0")/.." && exec backend/venv/bin/python applybot/apply.py --submit --limit "${APPLY_LIMIT:-10}" "$@"
