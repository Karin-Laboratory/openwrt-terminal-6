#!/bin/sh
# QEMU-only Air6 P43/P44 split test v0.2. Never use on real eMMC.
# Controlled fault injection: after-resize, after-gpt, before-format.
set -eu
DISK=/dev/vda
P43=/dev/vda43
P44=/dev/vda44
SECTORS=7634944
ORIG_P43_SECTORS=6170496
NEW_P43_SECTORS=927680
P44_SECTORS=5242816
START43=1464384
END43=2392063
START44=2392064
END44=7634879
OLD_END43=7634879
EXPECTED_GUID=797C3815-4B8E-47D1-9621-D0CFDCFF5724
EXT4_BLOCKS=112640
MARKER=N-UNIT-PRESERVE-TEST
say() { echo "[n-unit] $*"; }
fault() {
  [ "${N_UNIT_FAULT:-}" = "$1" ] || return 0
  say "FAULT_INJECTED=$1; stopping immediately for recovery test"
  exit 75
}
fail() { say "BLOCKED: $*" >&2; exit 1; }
get_size() { cat "/sys/class/block/$1/size"; }
get_info() { /sbin/sgdisk -i "$1" "$DISK" 2>/dev/null; }
get_guid() { get_info 43 | /bin/busybox awk '/^Partition unique GUID:/ {print $4; exit}'; }
get_start() { get_info "$1" | /bin/busybox awk '/^First sector:/ {print $3; exit}'; }
get_end() { get_info "$1" | /bin/busybox awk '/^Last sector:/ {print $3; exit}'; }
fs_blocks() {
  dd if="$P43" bs=1 skip=1028 count=4 2>/dev/null |
    /bin/busybox od -An -tu4 | /bin/busybox tr -d '[:space:]'
}
check_mounts() {
  if /bin/busybox awk -v a="$P43" -v b="$P44" '$1==a || $1==b {found=1} END {exit !found}' /proc/mounts; then
    fail "P43 or P44 is mounted"
  fi
}
check_p43_data() {
  mkdir -p /mnt/p43
  mount -t ext4 -o ro,noload "$P43" /mnt/p43 || fail "cannot read-only mount P43"
  if ! /bin/busybox grep -qx "$MARKER" /mnt/p43/preserve-test.txt; then
    umount /mnt/p43 || :
    fail "P43 preserved test data mismatch"
  fi
  umount /mnt/p43 || fail "cannot unmount P43"
  say "P43_DATA_PRESERVED_PASS"
}
run_fsck() {
  set +e
  /sbin/e2fsck -f -p "$P43"
  rc=$?
  set -e
  [ "$rc" -le 1 ] || fail "e2fsck exit=$rc"
}
check_p44_mount() {
  mkdir -p /mnt/p44
  mount -t ext4 -o ro,noload "$P44" /mnt/p44 || return 1
  umount /mnt/p44 || fail "cannot unmount P44"
  return 0
}
[ "${1:-}" = --check ] || [ "${1:-}" = --apply ] || {
  echo "Usage: /bin/sh $0 --check|--apply" >&2; exit 2;
}
MODE=$1
[ -b "$DISK" ] && [ -b "$P43" ] || fail "QEMU virtio disk not found"
[ ! -e /dev/mmcblk0 ] || fail "an eMMC is present; not a QEMU-only environment"
[ "$(get_size vda)" = "$SECTORS" ] || fail "unexpected disk sector count"
/sbin/sgdisk -v "$DISK" || fail "GPT validation failed"
[ "$(get_guid)" = "$EXPECTED_GUID" ] || fail "unexpected P43 GUID"
[ "$(get_start 43)" = "$START43" ] || fail "unexpected P43 start"
check_mounts
if [ "$(get_end 43)" = "$OLD_END43" ] && [ ! -e "$P44" ]; then
  [ "$(get_size vda43)" = "$ORIG_P43_SECTORS" ] || fail "old P43 device size mismatch"
  stage=ORIGINAL_GPT
elif [ "$(get_end 43)" = "$END43" ] && [ "$(get_start 44)" = "$START44" ] && [ "$(get_end 44)" = "$END44" ]; then
  [ "$(get_size vda43)" = "$NEW_P43_SECTORS" ] || fail "P43 kernel table stale: reboot QEMU"
  [ -b "$P44" ] || fail "P44 kernel table stale: reboot QEMU"
  [ "$(get_size vda44)" = "$P44_SECTORS" ] || fail "P44 kernel table stale: reboot QEMU"
  stage=SPLIT_GPT
else
  fail "unknown or interrupted GPT layout: manual recovery required"
fi
blocks=$(fs_blocks)
say "stage=$stage ext4_blocks=$blocks mode=$MODE"
case "$blocks" in 771312|112640) : ;; *) fail "unexpected ext4 size ($blocks blocks)" ;; esac
if [ "$stage" = SPLIT_GPT ] && [ "$blocks" != "$EXT4_BLOCKS" ]; then
  fail "split GPT but ext4 not shrunk"
fi
if [ "$MODE" = --check ]; then
  if [ "$stage" = SPLIT_GPT ]; then
    check_p43_data
    if check_p44_mount; then
      say "P44_MOUNT_PASS"
    else
      say "P44 is not mountable as ext4 (unformatted or damaged); no writes performed"
    fi
  fi
  say "QEMU_LAYOUT_CHECK_PASS"
  exit 0
fi
# --apply: only disposable QEMU image with independently verified backup.
if [ "$stage" = ORIGINAL_GPT ]; then
  if [ "$blocks" = 771312 ]; then
    run_fsck
    /sbin/resize2fs "$P43" 440M || fail "resize2fs failed"
    [ "$(fs_blocks)" = "$EXT4_BLOCKS" ] || fail "ext4 block count mismatch after shrink"
    run_fsck
    say "P43_EXT4_SHRINK_PASS"
    fault after-resize
  fi
  check_p43_data
  say "writing GPT: 43 -> 453MiB; creating 44"
  /sbin/sgdisk -d 43 -n 43:"$START43":"$END43" -t 43:8300 \
    -u 43:"$EXPECTED_GUID" -c 43:user_data \
    -n 44:"$START44":"$END44" -t 44:8300 -c 44:rootfs_data "$DISK" \
    || fail "GPT write failed; inspect before reboot"
  /sbin/sgdisk -v "$DISK" || fail "GPT invalid after write"
  [ "$(get_start 44)" = "$START44" ] || fail "P44 start mismatch"
  [ "$(get_end 44)" = "$END44" ] || fail "P44 end mismatch"
  say "GPT_SPLIT_PASS_REBOOT_QEMU_TO_CONTINUE"
  fault after-gpt
  exit 0
fi
check_p43_data
if check_p44_mount; then
  say "P44 already readable; will NOT reformat"
else
  fault before-format
  [ -f /allow-new-p44-format ] || fail "P44 unreadable. Create /allow-new-p44-format only after verifying it is empty"
  /sbin/mkfs.ext4 -F -L rootfs_data "$P44" || fail "mkfs.ext4 failed"
  check_p44_mount || fail "new P44 ext4 mount failed"
fi
say "N_UNIT_PARTITION_SPLIT_PASS"
