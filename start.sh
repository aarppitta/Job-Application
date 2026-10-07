#!/bin/bash
# Starts the whole app: backend (port 8001) + frontend (port 5001). Stop with Ctrl+C.
# Usage:  ./start.sh
cd "$(dirname "$0")"

# First run only: settings file, database, installs
[ -f .env ] || cp .env.example .env
createdb germany_jobs 2>/dev/null || true
# Use backend/venv if you created it, otherwise backend/.venv
VENV=backend/.venv
[ -x backend/venv/bin/python ] && VENV=backend/venv
if ! "$VENV/bin/python" -c "import sqlalchemy, fastapi" 2>/dev/null; then
  echo "Installing backend packages (first run)..."
  python3 -m venv "$VENV" && "$VENV/bin/pip" install -q -r backend/requirements.txt
fi

# Stop old copies of this app so ports 8001/5001 are free ("Address already in use")
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "germany-job-automation/frontend/node_modules/.bin/vite" 2>/dev/null
sleep 1
if [ ! -d frontend/node_modules ]; then
  echo "Installing frontend packages (first run)..."
  (cd frontend && npm install)
fi

# Backend: always the project's own Python (backend/venv or .venv), never the system Python.
(cd backend && "../$VENV/bin/python" -m uvicorn app.main:app --reload --port 8001) &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null' EXIT

echo ""
echo "Open http://localhost:5001  (login: see MASTER_USERNAME / MASTER_PASSWORD in .env)"
echo ""
cd frontend && npm run dev
