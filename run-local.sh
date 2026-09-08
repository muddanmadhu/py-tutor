#!/usr/bin/env bash
#
# Start PyForge locally: the API on :8000 and the web app on :5173.
#
#   ./run-local.sh
#
# Run this from a normal terminal. It cannot run inside a sandbox that forbids
# binding listening sockets — if you see "Operation not permitted" on bind, that
# is the sandbox, not this script.
#
# Ctrl-C stops both servers.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
VENV_PY="$ROOT/backend/.venv/bin/python"

info()  { printf '\033[36m==>\033[0m %s\n' "$*"; }
warn()  { printf '\033[33m!!\033[0m  %s\n' "$*"; }
die()   { printf '\033[31mxx\033[0m  %s\n' "$*" >&2; exit 1; }

# --- prerequisites ---------------------------------------------------------

if [ ! -x "$VENV_PY" ]; then
  info "No backend virtualenv found; creating one."
  PY312="$(command -v python3.12 || echo /opt/homebrew/opt/python@3.12/bin/python3.12)"
  [ -x "$PY312" ] || die "Python 3.12 not found. Install it: brew install python@3.12"
  "$PY312" -m venv backend/.venv
  "$VENV_PY" -m pip install --quiet --upgrade pip
  info "Installing backend dependencies (this takes a minute)."
  "$VENV_PY" -m pip install --quiet -e "backend[dev,ai]"
fi

if [ ! -d frontend/node_modules ]; then
  info "Installing frontend dependencies."
  ( cd frontend && npm install --no-audit --no-fund )
fi

if [ ! -f .env ]; then
  info "Creating .env with a fresh signing key."
  SECRET="$("$VENV_PY" -c 'import secrets; print(secrets.token_urlsafe(48))')"
  cat > .env <<EOF
PYFORGE_ENV=development
PYFORGE_DEBUG=true
PYFORGE_SECRET_KEY=$SECRET
PYFORGE_DATABASE_URL=sqlite+pysqlite:///./pyforge.db
PYFORGE_EXECUTOR=subprocess
PYFORGE_CORS_ORIGINS=http://localhost:$WEB_PORT,http://127.0.0.1:$WEB_PORT
PYFORGE_REDIS_URL=
PYFORGE_ANTHROPIC_API_KEY=
EOF
fi

if [ ! -f backend/pyforge.db ]; then
  info "Seeding the curriculum."
  ( cd backend && "$VENV_PY" -m app.db.init_db --seed --demo )
fi

# --- warn about the executor ----------------------------------------------

if grep -q '^PYFORGE_EXECUTOR=subprocess' .env 2>/dev/null; then
  warn "EXECUTOR=subprocess — learner code runs on this host WITHOUT container"
  warn "isolation. Fine for looking around; never expose this to anyone else."
  warn "For real isolation: install Docker, then 'make up'."
fi

# --- launch ----------------------------------------------------------------

PIDS=()
cleanup() {
  echo
  info "Stopping servers."
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

info "Starting API on http://127.0.0.1:$API_PORT"
( cd backend && exec "$ROOT/backend/.venv/bin/uvicorn" app.main:app \
    --host 127.0.0.1 --port "$API_PORT" --reload ) &
PIDS+=($!)

info "Starting web app on http://localhost:$WEB_PORT"
( cd frontend && VITE_API_BASE_URL="http://127.0.0.1:$API_PORT" \
    exec npx vite --host 127.0.0.1 --port "$WEB_PORT" --strictPort ) &
PIDS+=($!)

# Wait for the API to answer before printing the banner.
for _ in $(seq 1 40); do
  sleep 0.5
  if curl -sf -m 2 "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1; then
    break
  fi
done

cat <<BANNER

  ────────────────────────────────────────────────────────────────
   PyForge is running

     Web app        http://localhost:$WEB_PORT
     API docs       http://127.0.0.1:$API_PORT/docs
     Health         http://127.0.0.1:$API_PORT/health

     Demo login     learner@example.com / demo-password-123

   Try: Learn → "What Python Is" → run the editor on the right,
        then Practice → FizzBuzz → Submit to watch mastery move.

   Ctrl-C to stop.
  ────────────────────────────────────────────────────────────────

BANNER

wait
