#!/usr/bin/env bash
# Start both Aether dev servers. CTRL+C kills both cleanly.

set -e

BACKEND_PORT=8080
FRONTEND_PORT=5173
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && wait "$BACKEND_PID" 2>/dev/null
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && wait "$FRONTEND_PID" 2>/dev/null
  echo "Done."
  exit 0
}
trap cleanup INT TERM

# Kill anything already on our ports (Windows)
for port in $BACKEND_PORT $FRONTEND_PORT; do
  pids=$(netstat -ano 2>/dev/null | grep ":${port}.*LISTENING" | awk '{print $5}' | sort -u)
  for pid in $pids; do
    [ "$pid" != "0" ] && taskkill //F //PID "$pid" 2>/dev/null || true
  done
done

sleep 1

# Start backend
cd backend
python -m uvicorn aether.main:app --reload --host 127.0.0.1 --port $BACKEND_PORT &
BACKEND_PID=$!
cd ..

# Start frontend
cd frontend
npx vite --port $FRONTEND_PORT &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo "  Backend:  http://127.0.0.1:$BACKEND_PORT"
echo "  Press CTRL+C to stop both"
echo "========================================"
echo ""

# Wait for either to exit
wait
