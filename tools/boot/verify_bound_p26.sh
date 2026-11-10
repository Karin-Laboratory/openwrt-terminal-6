#!/bin/sh
# SPDX-License-Identifier: MIT
# Standalone, fail-closed exact P26 identity check for early Air6 initramfs.
# No partition writes, mounting, signing or private device data.
# Default paths refer only to known public partition naming; overridable
# for host-only synthetic tests.
manifest=${1:-/etc/air6/p26.sha256}
device=${2:-/dev/mmcblk0p26}
[ -f "$manifest" ] && [ ! -L "$manifest" ] && [ -r "$manifest" ] || exit 11
[ -e "$device" ] && [ ! -L "$device" ] && [ -r "$device" ] || exit 12
record=$(cat "$manifest") || exit 13
expected=${record%% *}
[ "${#expected}" -eq 64 ] || exit 14
case "$expected" in *[!0123456789abcdef]*) exit 14 ;; esac
[ "$record" = "$expected  $device" ] || exit 15
actual_record=$(sha256sum "$device" 2>/dev/null) || exit 16
actual=${actual_record%% *}
[ "$actual" = "$expected" ] || exit 17
printf '%s\n' 'P26_RUNTIME_FULL_SHA256_PASS'
exit 0
