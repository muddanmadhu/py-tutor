#!/usr/bin/env bash
#
# Build the static site on a hosted CI runner (Render, Netlify, Cloudflare Pages).
#
# Kept as a script rather than a one-line buildCommand because it needs to do
# three things in order and fail loudly on each: install the backend (only so the
# content exporter can import it), generate the content tree, then build the web
# app. Inlining that into YAML makes failures hard to read and impossible to
# reproduce locally.
#
# Run it locally exactly as the host does:
#
#   ./render-build.sh
#
# The result is frontend/dist, ready to serve from a domain root.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

info() { printf '\033[36m==>\033[0m %s\n' "$*"; }
die()  { printf '\033[31mxx\033[0m  %s\n' "$*" >&2; exit 1; }

# --- Python: only needed to run the exporter -------------------------------
#
# Prefer a local virtualenv when one exists, so this script behaves identically
# on a developer machine and on a build runner that has none.

if [ -x "$ROOT/backend/.venv/bin/python" ]; then
  PY="$ROOT/backend/.venv/bin/python"
  info "Using the existing virtualenv"
else
  PY="$(command -v python3 || command -v python)" || die "No Python interpreter found."
  info "Installing the backend with $($PY --version)"
  # --user keeps this working on images where site-packages is not writable.
  # Only the base dependencies are needed; nothing here runs the API or tests.
  "$PY" -m pip install --user --quiet --upgrade pip
  "$PY" -m pip install --user --quiet -e ./backend
fi

info "Exporting curriculum, grader and reviewer"
"$PY" tools/export_static.py

# --- Web app ---------------------------------------------------------------

command -v npm >/dev/null || die "npm is not available on this build image."

info "Installing web dependencies"
cd "$ROOT/frontend"
if [ -f package-lock.json ]; then
  npm ci --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi

info "Checking types and lint"
npm run typecheck
npm run lint

# `build:root` sets Vite's base to `/`, because these hosts serve from a domain
# root — unlike a GitHub Pages project page, which serves from /py-tutor/.
# No VITE_API_BASE_URL is set, and its absence is what selects the static
# implementation in src/api/endpoints.ts.
info "Building (base=/, static mode)"
npm run build:root

# A bundle without content looks healthy and then shows an empty curriculum to
# every visitor, so fail the build here instead.
for required in content/courses.json content/grader.py content/reviewer.py index.html; do
  [ -f "dist/$required" ] || die "dist/$required is missing; the build is incomplete."
done

info "Done: $(find dist/content -type f | wc -l | tr -d ' ') content files, $(du -sh dist | cut -f1) total"
