#!/bin/sh
# SPDX-License-Identifier: MIT
# Public RC14-derived management candidate. Never auto-started.
# Deliberately no OEM data, synthetic NETSYS registration or SGMII writes.
set -eu
umask 077
PATH=/sbin:/bin:/usr/sbin:/usr/bin
export PATH

log() { printf 'SBA6D_PUBLIC_MGMT_%s\n' "$1" >/dev/console 2>/dev/null || :; }
fail() { log "BLOCKED_$1"; exit 1; }
case "${1:-}" in
    --check|--start) action=$1 ;;
    *) printf 'usage: %s --check|--start\n' "$0" >&2; exit 2 ;;
esac
# A device-specific key/provisioning tool runs separately. Boot must NEVER
# manufacture reusable shared passwords, SSH keys or MAC addresses.
[ "$(id -u)" = 0 ] || fail NOT_ROOT
grep -qw 'bootslot=a' /proc/cmdline || fail NOT_SLOT_A
awk '$2=="/overlay" && $3=="ext4" && $4 ~ /(^|,)rw(,|$)/ {ok=1} END {exit !ok}' /proc/mounts ||
    fail P44_RW_NOT_MOUNTED
[ -f /rom/etc/preinit ] && [ -x /rom/sbin/procd ] || fail VERIFIED_ROM_NOT_VISIBLE
# No runtime external modules are loaded here. The production native DTB must
# already have registered the built-in MAC1 -> DSA CPU5 -> lan2 topology.
[ -e /sys/class/net/eth1 ] || fail NETSYS_MAC1_ABSENT
[ -e /sys/class/net/lan2 ] || fail DSA_LAN2_ABSENT
[ "$(cat /sys/class/net/lan2/carrier 2>/dev/null)" = 1 ] || fail LAN2_NO_CARRIER
[ "$(cat /sys/class/net/lan2/duplex 2>/dev/null)" = full ] || fail LAN2_NOT_FULL_DUPLEX
# The validated RC14 C path was 1000/full. No hardcoded MAC or SGMII writes.
[ "$(cat /sys/class/net/lan2/speed 2>/dev/null)" = 1000 ] || fail LAN2_NOT_1000
command -v ip >/dev/null 2>&1 || fail IP_TOOL_MISSING
command -v dropbear >/dev/null 2>&1 || fail DROPBEAR_MISSING
secret_dir=/overlay/sba6d/ssh
[ -d "$secret_dir" ] && [ ! -L "$secret_dir" ] || fail SSH_PROVISIONING_MISSING
[ "$(stat -c '%u:%g:%a' "$secret_dir" 2>/dev/null)" = 0:0:700 ] ||
    fail SSH_DIR_OWNER_MODE
for name in hostkey_ed25519 authorized_keys; do
    file="$secret_dir/$name"
    [ -f "$file" ] && [ ! -L "$file" ] && [ -s "$file" ] ||
        fail SSH_SECRET_MISSING
    [ "$(stat -c '%u:%g:%a' "$file" 2>/dev/null)" = 0:0:600 ] ||
        fail SSH_SECRET_OWNER_MODE
done
# Only an owner-provisioned persistent P44 key is accepted. Never generate or
# replace it in the management bring-up path.
grep -q '^ssh-' "$secret_dir/authorized_keys" || fail SSH_AUTHORIZED_KEY_FORMAT
case "$action" in
    --check) log PREFLIGHT_PASS; exit 0 ;;
esac
lock=/tmp/sba6d-public-mgmt-start.lock
mkdir "$lock" 2>/dev/null || fail START_ALREADY_ATTEMPTED
# Network application remains a deliberate owner action. This candidate
# requires an address already configured by the native OpenWrt network stack;
# it does not replace addresses or bring interfaces down during trial.
ip -4 addr show dev lan2 | grep -Fq 'inet 192.168.1.1/24' ||
    fail LAN2_MANAGEMENT_ADDRESS_MISSING
# Never assume an existing TCP/22 listener is ours.
awk '$2=="0101A8C0:0016" && $4=="0A" {found=1} END {exit !found}' /proc/net/tcp &&
    fail EXISTING_SSH_LISTENER
log DROPBEAR_START
dropbear -F -E -s -g -j -k -p 192.168.1.1:22 \
    -r "$secret_dir/hostkey_ed25519" -D "$secret_dir" \
    </dev/null >/tmp/sba6d-public-dropbear.log 2>&1 &
pid=$!
printf '%s\n' "$pid" > /tmp/sba6d-public-dropbear.pid
n=0
while [ "$n" -lt 10 ]; do
    if awk '$2=="0101A8C0:0016" && $4=="0A" {found=1} END {exit !found}' /proc/net/tcp; then
        log DROPBEAR_LISTEN_READY
        exit 0
    fi
    sleep 1
    n=$((n + 1))
done
kill -TERM "$pid" 2>/dev/null || :
fail DROPBEAR_LISTEN_TIMEOUT
