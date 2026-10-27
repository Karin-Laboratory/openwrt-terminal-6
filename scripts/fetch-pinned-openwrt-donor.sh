#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Inspect four PUBLIC, pinned donor TEXT files only. Never check out its tree.
set -euo pipefail
umask 077

DONOR_REPO='https://github.com/13179415360/openwrt-mt6990-lg6851f.git'
DONOR_REV='a40df9a5afb46716dea799acea69f17480df4d82'
DEST="${1:-donor-source-inspection}"

if (( EUID == 0 )); then
  echo 'Refusing external source acquisition as root' >&2
  exit 2
fi
for tool in git mktemp mkdir mv timeout wc; do
  command -v "$tool" >/dev/null || { echo "Missing host tool: $tool" >&2; exit 2; }
done
if [[ -z "$DEST" || "$DEST" == "/" || "$DEST" == "." || "$DEST" == ".." || -e "$DEST" || -L "$DEST" ]]; then
  echo 'Provide a NEW non-existing destination' >&2
  exit 2
fi
parent="$(dirname -- "$DEST")"
if [[ ! -d "$parent" || -L "$parent" ]]; then
  echo 'Destination parent must exist and not be a symlink' >&2
  exit 2
fi

temporary="$(mktemp -d "${TMPDIR:-/tmp}/sbat6-donor-text.XXXXXXXX")"
trap 'rm -rf -- "$temporary"' EXIT
git -C "$temporary" init -q source
git -C "$temporary/source" remote add origin "$DONOR_REPO"
# The partial-fetch filter prevents downloading every donor firmware blob.
# No working-tree checkout of any commit is ever performed.
timeout 180s git -C "$temporary/source" -c protocol.version=2 \
  fetch --quiet --no-tags --depth=1 --filter=blob:none origin "$DONOR_REV"
actual="$(git -C "$temporary/source" rev-parse 'FETCH_HEAD^{commit}')"
test "$actual" = "$DONOR_REV"

mkdir -p "$temporary/output"
# Pinned object IDs were independently verified against the public repo.
# No device images, Wi-Fi EEPROM, modem NV, binaries, scripts or packages.
paths=(
  'feeds.conf.default'
  'target/linux/mediatek/Makefile'
  'target/linux/mediatek/mt6990/target.mk'
  'target/linux/mediatek/image/mt6990.mk'
)
ids=(
  '05f5c8c47c7ae4161067e045f579ddf46c4fe77f'
  '77b27878987e53e83be3d40dc342753e3734ac75'
  'c98113e8a8cc9ee334eef28428972d8e9d4404e7'
  '714551500ccd45bd3dfc77f951f104e0c46a660b'
)
for i in "${!paths[@]}"; do
  path="${paths[$i]}"
  expected="${ids[$i]}"
  blob="$(git -C "$temporary/source" rev-parse "${DONOR_REV}:${path}")"
  if [[ "$blob" != "$expected" ]]; then
    echo "Donor text identity mismatch: $path" >&2
    exit 3
  fi
  out="$temporary/output/$path"
  mkdir -p "$(dirname -- "$out")"
  timeout 45s git -C "$temporary/source" cat-file blob "$blob" > "$out"
  test "$(git hash-object -- "$out")" = "$expected"
  test "$(wc -c < "$out")" -le 16384
done

# Publish only the four allowlisted text files. Temporary Git objects
# (including tree metadata) are discarded without persisting a clone.
mv -- "$temporary/output" "$DEST"
echo 'DONOR_TEXT_ALLOWLIST_4_BLOBS_PASS'
echo 'No vendor image, firmware, radio calibration or signing material included.'
echo 'SOURCE INSPECTION ONLY: no build, rootfs package, flash or deployment.'
