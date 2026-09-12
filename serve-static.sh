#!/usr/bin/env bash
#
# Build the static site and serve it locally.
#
#   ./serve-static.sh                 # build if needed, then serve on :4173
#   ./serve-static.sh --rebuild       # always rebuild first
#   ./serve-static.sh --port 8080
#   ./serve-static.sh --no-build      # serve whatever is in frontend/dist
#
# This is the no-backend build: the same bundle a static host publishes. The
# curriculum is pre-rendered JSON and Python runs in the browser under Pyodide,
# so there is no API, no database and no login.
#
# It builds with --base=/ because a local server serves from the root. GitHub
# Pages serves a project page from /py-tutor/ instead, so publishing there uses
# `npm run build` (the default base) — see docs/DEPLOY_GITHUB_PAGES.md.
#
# Run this from a normal terminal. It cannot bind a port inside a sandbox that
# forbids listening sockets.
#
# Ctrl-C stops the server.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PORT="${PORT:-4173}"
BUILD=auto
DIST="$ROOT/frontend/dist"
VENV_PY="$ROOT/backend/.venv/bin/python"

while [ $# -gt 0 ]; do
  case "$1" in
    --rebuild)  BUILD=always; shift ;;
    --no-build) BUILD=never;  shift ;;
    --port)     PORT="$2";    shift 2 ;;
    # awk rather than a `sed` line range: the range needs updating whenever the
    # header changes, and `\s` is a GNU extension that BSD sed on macOS ignores.
    -h|--help)  awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"; exit 0 ;;
    *)          echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

info() { printf '\033[36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33m!!\033[0m  %s\n' "$*"; }
die()  { printf '\033[31mxx\033[0m  %s\n' "$*" >&2; exit 1; }

command -v node >/dev/null || die "node is not installed. Install Node 20 or newer."

# --- decide whether to build ------------------------------------------------

if [ "$BUILD" = auto ] && [ ! -f "$DIST/index.html" ]; then
  BUILD=always
fi

if [ "$BUILD" = always ]; then
  command -v npm >/dev/null || die "npm is not installed."

  if [ ! -d frontend/node_modules ]; then
    info "Installing web dependencies."
    ( cd frontend && npm install --no-audit --no-fund )
  fi

  # Regenerate the curriculum when the backend virtualenv is here, so a content
  # edit shows up without a separate step. The tree is committed, so a machine
  # without the venv still builds — that is what the static hosts rely on.
  if [ -x "$VENV_PY" ]; then
    info "Regenerating content from the curriculum."
    "$VENV_PY" tools/export_static.py
  else
    warn "No backend virtualenv; using the committed content tree."
  fi

  info "Checking types and lint."
  ( cd frontend && npm run typecheck && npm run lint )

  info "Building (base=/, static mode)."
  ( cd frontend && npm run build:root )

  # A bundle without content looks healthy and then shows an empty curriculum,
  # so fail here rather than at the first click.
  for required in content/courses.json content/grader.py content/reviewer.py index.html; do
    [ -f "$DIST/$required" ] || die "dist/$required is missing; the build is incomplete."
  done
fi

[ -f "$DIST/index.html" ] || die "Nothing built. Drop --no-build, or run ./serve-static.sh --rebuild."

# --- serve ------------------------------------------------------------------

info "Serving $DIST"
exec node tools/static_server.mjs --dir "$DIST" --port "$PORT"
