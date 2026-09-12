#!/usr/bin/env bash
#
# Build the static site on a hosted CI runner (Render, Netlify, Cloudflare Pages).
#
# The content tree is committed, so this build needs **Node only**. Static-site
# build images are Node-focused: Python may be absent, and where it is present a
# PEP 668 "externally managed environment" refuses `pip install`. Depending on it
# made the deploy fail on exactly the hosts this script exists to serve.
#
# The exporter still runs when Python is available, so a local build always picks
# up curriculum edits immediately. When it is not, the committed tree is used and
# CI guarantees that tree is current — .github/workflows/ci.yml re-exports and
# fails if the result differs from what is committed.
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
warn() { printf '\033[33m!!\033[0m  %s\n' "$*"; }
die()  { printf '\033[31mxx\033[0m  %s\n' "$*" >&2; exit 1; }

CONTENT="$ROOT/frontend/public/content"

# --- Content: regenerate if we can, otherwise use the committed tree --------

regenerate() {
  if [ -x "$ROOT/backend/.venv/bin/python" ]; then
    info "Regenerating content with the local virtualenv"
    "$ROOT/backend/.venv/bin/python" tools/export_static.py
    return 0
  fi

  local py
  py="$(command -v python3 || command -v python || true)"
  [ -n "$py" ] || return 1

  # An isolated venv rather than `pip install --user`, which PEP 668 rejects on
  # current Debian and Ubuntu images.
  if "$py" -m venv /tmp/pyforge-export >/dev/null 2>&1; then
    info "Regenerating content with a temporary venv ($("$py" --version 2>&1))"
    /tmp/pyforge-export/bin/pip install --quiet --upgrade pip >/dev/null 2>&1 || true
    /tmp/pyforge-export/bin/pip install --quiet -e ./backend || return 1
    /tmp/pyforge-export/bin/python tools/export_static.py || return 1
    return 0
  fi
  return 1
}

if regenerate; then
  :
else
  warn "No usable Python on this image; using the committed content tree."
  warn "CI verifies that tree is current, so this is expected on a static host."
  [ -f "$CONTENT/courses.json" ] || die "No Python *and* no committed content — cannot build."
fi

[ -f "$CONTENT/grader.py" ] || die "$CONTENT/grader.py is missing; grading would not work."
[ -f "$CONTENT/reviewer.py" ] || die "$CONTENT/reviewer.py is missing; code review would not work."
info "Content ready: $(find "$CONTENT" -type f | wc -l | tr -d ' ') files"

# --- Web app ---------------------------------------------------------------

command -v npm >/dev/null || die "npm is not available on this build image."

# Printed unconditionally: the first Render build failed with npm's opaque
# "Exit handler never called!", and knowing the toolchain would have identified
# it immediately. .node-version pins this, but a host that ignores that file
# should be visible in the log rather than inferred.
info "Toolchain: node $(node --version 2>/dev/null || echo '?'), npm $(npm --version 2>/dev/null || echo '?')"

info "Installing web dependencies"
cd "$ROOT/frontend"

# Render has died here with npm's "Exit handler never called!". That message
# means npm was terminated before it could run its own exit handler, so it
# describes the symptom and says nothing about the cause. The ladder below
# addresses the plausible causes in order, because the log cannot tell them
# apart and each rung costs more than the last.
#
# Unpacking the tree is the memory-hungry phase, and being OOM-killed is the
# most common way a process exits without its handler running. The default heap
# on a small build container is what tips it over.
export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=2048}"

npm_flags=(--no-audit --no-fund)

# Rungs 2 and 3 install through a throwaway cache. Render persists its cache
# directory between builds, so one corrupted entry fails every future deploy
# identically — which is what `npm ci` and `npm install` both dying the same
# way looks like. This is not the default because discarding a warm cache means
# re-downloading the whole tree, which is a real cost to pay on every build for
# a fault that may never recur.
fresh_cache=(--cache "$(mktemp -d)/npm" --maxsockets 1)

if [ -f package-lock.json ]; then
  # `npm ci` is preferred — it installs exactly the locked tree. But it aborts
  # on any mismatch with the lockfile, and on some images it dies inside npm
  # itself, so each fallback is logged loudly rather than passed over.
  if ! npm ci "${npm_flags[@]}"; then
    warn "npm ci failed; retrying with a throwaway cache on a single connection"
    rm -rf node_modules
    if ! npm ci "${npm_flags[@]}" "${fresh_cache[@]}"; then
      warn "npm ci failed again; falling back to npm install (resolves rather than replays the lockfile)"
      rm -rf node_modules
      npm install "${npm_flags[@]}" "${fresh_cache[@]}"
    fi
  fi
else
  npm install "${npm_flags[@]}"
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
