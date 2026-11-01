#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Isolated QEMU virt boot of the exact unsigned ARM64 Image built in this CI.
# No NIC, host device passthrough, firmware installation, signer or credentials.
set -euo pipefail
if [[ $# -ne 1 || "$1" != /* || ! -s "$1" ||
      "$(uname -m)" != aarch64 || "$(id -u)" -eq 0 ]]; then
  echo 'usage: smoke-arm64-procd-guest.sh /absolute/ARM64/Image (non-root aarch64)' >&2
  exit 2
fi
command -v qemu-system-aarch64 >/dev/null
log="$(mktemp "${TMPDIR:-/tmp}/sbat6-qemu-boot.XXXXXXXX")"
trap 'rm -f -- "$log"' EXIT
status=0
timeout --signal=TERM --kill-after=5s 120s qemu-system-aarch64 \
  -machine virt -cpu cortex-a57 -accel tcg -m 768 -smp 2 \
  -display none -serial stdio -monitor none -nic none -no-reboot \
  -kernel "$1" -append 'console=ttyAMA0 loglevel=7 panic=1 sbat6.qemu_bridge_smoke=1' \
  >"$log" 2>&1 || status=$?
tail -n 100 "$log"
if [[ "$status" -ne 0 && "$status" -ne 124 ]]; then
  echo "SBAT6_QEMU_GUEST_BOOT_FAIL: qemu exit $status" >&2
  exit 1
fi
if grep -Fq 'Kernel panic' "$log"; then
  echo 'SBAT6_QEMU_GUEST_BOOT_FAIL: kernel panic' >&2
  exit 1
fi
if ! grep -Fq 'SBAT6_PROCD_NETIFD_REGISTERED' "$log"; then
  echo 'SBAT6_QEMU_GUEST_BOOT_FAIL: procd service registration not observed' >&2
  exit 1
fi
if ! grep -Fq 'SBAT6_NETIFD_PROCESS_STABLE_RUNTIME_PASS' "$log"; then
  echo 'SBAT6_QEMU_GUEST_BOOT_FAIL: stable netifd process not observed after registration' >&2
  exit 1
fi
if ! grep -Fq 'SBAT6_NETIFD_EMPTY_BRIDGE_RUNTIME_PASS' "$log"; then
  echo 'SBAT6_QEMU_GUEST_BOOT_FAIL: netifd-created bridge not observed' >&2
  exit 1
fi
echo 'SBAT6_QEMU_VIRT_PROCD_NETIFD_BRIDGE_RUNTIME_PASS'
echo 'LIMIT: QEMU virt only; an empty isolated netifd bridge is not Ethernet traffic, Air6 boot, Wi-Fi AP or rights proof.'
