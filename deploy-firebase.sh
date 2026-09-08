#!/usr/bin/env bash
#
# Build and publish the static site to Firebase Hosting.
#
#   ./deploy-firebase.sh              # deploy to the live channel
#   ./deploy-firebase.sh --preview    # deploy to a temporary preview URL
#
# One-time setup (needs a browser, so it cannot be scripted):
#
#   npm install -g firebase-tools
#   firebase login
#   firebase use --add          # pick your project; writes .firebaserc
#
# Hosting is on the free Spark plan — no billing card. Nothing here needs Blaze,
# because the site is entirely static.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

VENV_PY="$ROOT/backend/.venv/bin/python"

info() { printf '\033[36m==>\033[0m %s\n' "$*"; }
die()  { printf '\033[31mxx\033[0m  %s\n' "$*" >&2; exit 1; }

command -v firebase >/dev/null || die "firebase-tools is not installed. Run: npm install -g firebase-tools"
[ -x "$VENV_PY" ] || die "No backend virtualenv. Run ./run-local.sh once to create it."

if [ ! -f .firebaserc ]; then
  die "No Firebase project selected yet. Run: firebase use --add"
fi

# The content tree is generated, never committed, so it cannot go stale against
# the seed curriculum. Regenerate on every deploy.
info "Exporting curriculum, grader and reviewer"
"$VENV_PY" tools/export_static.py

info "Installing web dependencies"
( cd frontend && npm ci --no-audit --no-fund )

info "Checking types and lint"
( cd frontend && npm run typecheck && npm run lint )

# `build:root` sets Vite's base to `/`, because Firebase serves from the domain
# root — unlike a GitHub Pages project page, which serves from /py-tutor/.
# No VITE_API_BASE_URL is set, and its absence is what selects the static
# implementation in src/api/endpoints.ts.
info "Building (base=/, static mode)"
( cd frontend && npm run build:root )

# A build that ships without content looks healthy and then shows an empty
# curriculum to every visitor, so fail here rather than there.
for required in content/courses.json content/grader.py content/reviewer.py index.html; do
  [ -f "frontend/dist/$required" ] || die "frontend/dist/$required is missing; the build is incomplete."
done
info "Bundle verified: $(find frontend/dist/content -type f | wc -l | tr -d ' ') content files"

if [ "${1:-}" = "--preview" ]; then
  info "Deploying to a preview channel"
  firebase hosting:channel:deploy "preview-$(date +%Y%m%d-%H%M%S)" --expires 7d
else
  info "Deploying to live"
  firebase deploy --only hosting
fi
