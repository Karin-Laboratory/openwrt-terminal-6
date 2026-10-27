#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Download public upstream MT6990 donor SOURCE only. NEVER build/install.
set -euo pipefail

DONOR_REPO='https://github.com/13179415360/openwrt-mt6990-lg6851f.git'
DONOR_REV='a40df9a5afb46716dea799acea69f17480df4d82'
DEST="${1:-donor-source}"

if [[ $EUID -eq 0 ]]; then
  echo 'Refusing source acquisition as root' >&2
  exit 2
fi
if [[ -z "$DEST" || "$DEST" == "/" || "$DEST" == "." || "$DEST" == ".." || -e "$DEST" ]]; then
  echo 'Provide a NEW non-existing source directory' >&2
  exit 2
fi
git clone --no-checkout --filter=blob:none -- "$DONOR_REPO" "$DEST"
git -C "$DEST" checkout --detach "$DONOR_REV"
actual="$(git -C "$DEST" rev-parse HEAD)"
if [[ "$actual" != "$DONOR_REV" ]]; then
  echo 'Pinned donor source commit mismatch' >&2
  exit 3
fi
echo "Donor source revision verified: $actual"
echo 'SOURCE ONLY. No signing, image build, deployment or device interaction.'
echo 'LG6851F image and rootfs assumptions are NOT valid for SBAT6.'
