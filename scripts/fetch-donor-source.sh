#!/usr/bin/env bash
# Source-only donor checkout. NEVER builds, signs, packages or flashes images.
set -euo pipefail
DONOR_URL=https://github.com/13179415360/openwrt-mt6990-lg6851f.git
DONOR_COMMIT=a40df9a5afb46716dea799acea69f17480df4d82
DEST="${1:-donor-source}"
[[ ! -e "$DEST" ]] || { echo "Destination already exists: $DEST" >&2; exit 2; }
git clone --no-checkout --filter=blob:none "$DONOR_URL" "$DEST"
git -C "$DEST" checkout --detach "$DONOR_COMMIT"
actual="$(git -C "$DEST" rev-parse HEAD)"
[[ "$actual" == "$DONOR_COMMIT" ]] || { echo "Unexpected donor commit" >&2; exit 3; }
printf 'Donor source pinned: %s\n' "$actual"
printf '%s\n' 'SOURCE ONLY: No make, signing, packaging, or hardware action has occurred.'
printf '%s\n' 'Do NOT build or flash LG6851F images on SoftBank Air Terminal 6.'
