#!/bin/sh
# SPDX-License-Identifier: MIT
# Experimental Air6 /init: owner-private P44 consent needed for RW mount.
# NOT enabled in public images. No fsck, format, signing, flash or reboot.
set -eu
umask 077

log() { printf '%s\n' "AIR6_$1" >/dev/console 2>/dev/null || :; }
halt_boot() {
    log "BOOT_BLOCKED_$1"
    # Do not exit PID1, reboot, fall back, alter slots or touch flash.
    while :; do sleep 3600; done
}
if [ "${1:-}" = "--capabilities" ]; then
    printf '%s\n' AIR6_P26_P44_BOOTSTRAP_SOURCE_ONLY P26_RO_SHA256 \
        P44_EXT4_RO_NOLOAD P44_EXPLICIT_RW_GO OVERLAYFS SWITCH_ROOT NO_AUTO_RECOVERY
    exit 0
fi
[ "$#" -eq 0 ] || exit 2
[ "$$" -eq 1 ] || halt_boot NOT_PID1
log RAM_INIT_ENTER

P26=/dev/mmcblk0p26
P44=/dev/mmcblk0p44
ROM=/mnt/air6-rom
UPPER=/mnt/air6-p44
NEWROOT=/mnt/air6-newroot
EXPECTED=/etc/air6-p26.sha256
P44_PARTNAME=/etc/air6-p44.partname
OWNER_GO=/etc/air6-owner-p44-rw-go

# Mount pseudo-filesystems first, then inspect actual device nodes and GPT.
mkdir -p /proc /sys /dev "$ROM" "$UPPER" "$NEWROOT" ||
    halt_boot MOUNTPOINT_CREATE
mount -t proc proc /proc || halt_boot PROC_MOUNT
mount -t sysfs sysfs /sys || halt_boot SYS_MOUNT
mount -t devtmpfs devtmpfs /dev || halt_boot DEV_MOUNT

[ -b "$P26" ] || halt_boot P26_NOT_BLOCK
[ -b "$P44" ] || halt_boot P44_NOT_BLOCK
grep -qx 'PARTNAME=rootfs_a' /sys/class/block/mmcblk0p26/uevent ||
    halt_boot P26_GPT_PARTNAME
[ -s "$P44_PARTNAME" ] && [ ! -L "$P44_PARTNAME" ] ||
    halt_boot P44_PARTNAME_UNREVIEWED
read -r partname < "$P44_PARTNAME" || halt_boot P44_PARTNAME_UNREADABLE
case "$partname" in
    ''|*[!a-zA-Z0-9_-]*) halt_boot P44_PARTNAME_INVALID ;;
esac
grep -qx "PARTNAME=$partname" /sys/class/block/mmcblk0p44/uevent ||
    halt_boot P44_GPT_PARTNAME

# Private owner approval is not included by public CI.
[ -f "$OWNER_GO" ] && [ ! -L "$OWNER_GO" ] ||
    halt_boot P44_RW_NOT_APPROVED
[ "$(cat "$OWNER_GO" 2>/dev/null)" = AIR6_P44_RW_OWNER_APPROVED_FOR_THIS_PAIR ] ||
    halt_boot P44_RW_TOKEN_NOT_MATCHED
[ -s "$EXPECTED" ] && [ ! -L "$EXPECTED" ] ||
    halt_boot P26_EXPECTED_SHA_MISSING
read -r expected < "$EXPECTED" || halt_boot P26_EXPECTED_SHA_UNREADABLE
[ "${#expected}" -eq 64 ] || halt_boot P26_EXPECTED_SHA_LENGTH
case "$expected" in
    *[!0-9a-f]*) halt_boot P26_EXPECTED_SHA_INVALID ;;
esac

# Hash entire padded partition before any P44 RW mount.
observed="$(sha256sum "$P26")" || halt_boot P26_SHA_READ_FAILURE
observed="${observed%% *}"
[ "$observed" = "$expected" ] || halt_boot P26_SHA_MISMATCH
log P26_RO_VERIFIED

mount -t squashfs -o ro "$P26" "$ROM" ||
    halt_boot P26_SQUASHFS_RO_MOUNT
[ -x "$ROM/sbin/init" ] && [ -f "$ROM/etc/preinit" ] ||
    halt_boot P26_INIT_PREINIT_MISSING
log P26_ROM_MOUNT_PASS

# Check P44 with journal replay disabled before owner-authorized RW mount.
mount -t ext4 -o ro,noload "$P44" "$UPPER" ||
    halt_boot P44_RO_NOLOAD_MOUNT
[ -d "$UPPER/upper" ] && [ ! -L "$UPPER/upper" ] ||
    halt_boot P44_UPPER_INVALID
[ -d "$UPPER/work" ] && [ ! -L "$UPPER/work" ] ||
    halt_boot P44_WORK_INVALID
[ ! -e "$UPPER/upper/etc/preinit" ] && [ ! -L "$UPPER/upper/etc/preinit" ] ||
    halt_boot P44_PREINIT_SHADOW
[ ! -e "$UPPER/upper/sbin/init" ] && [ ! -L "$UPPER/upper/sbin/init" ] ||
    halt_boot P44_INIT_SHADOW
[ ! -e "$UPPER/upper/etc/.wh.preinit" ] &&
    [ ! -e "$UPPER/upper/sbin/.wh.init" ] ||
    halt_boot P44_BOOT_WHITEOUT
log P44_RO_NOLOAD_PASS

umount "$UPPER" || halt_boot P44_RO_UMOUNT_FAILED
mount -t ext4 -o rw,noatime "$P44" "$UPPER" ||
    halt_boot P44_RW_MOUNT_FAILED
mount -t overlay overlay -o "lowerdir=$ROM,upperdir=$UPPER/upper,workdir=$UPPER/work" \
    "$NEWROOT" || halt_boot P44_OVERLAY_MOUNT_FAILED
[ -f "$NEWROOT/etc/preinit" ] && [ -x "$NEWROOT/sbin/init" ] ||
    halt_boot OVERLAY_BOOT_FILES_MISSING
# Verify that opaque xattrs/whiteouts did not mask the critical entrypoints.
cmp -s "$ROM/etc/preinit" "$NEWROOT/etc/preinit" ||
    halt_boot OVERLAY_PREINIT_CONTENT_CHANGED
cmp -s "$ROM/sbin/init" "$NEWROOT/sbin/init" ||
    halt_boot OVERLAY_INIT_CONTENT_CHANGED
log OVERLAY_MOUNT_PASS

mkdir -p "$NEWROOT/rom" "$NEWROOT/overlay" \
    "$NEWROOT/proc" "$NEWROOT/sys" "$NEWROOT/dev" ||
    halt_boot NEWROOT_MOUNTPOINT
mount --move "$ROM" "$NEWROOT/rom" || halt_boot MOVE_ROM
mount --move "$UPPER" "$NEWROOT/overlay" || halt_boot MOVE_P44
mount --move /proc "$NEWROOT/proc" || halt_boot MOVE_PROC
mount --move /sys "$NEWROOT/sys" || halt_boot MOVE_SYS
mount --move /dev "$NEWROOT/dev" || halt_boot MOVE_DEV
log SWITCH_ROOT_BEGIN
exec switch_root -c /dev/console "$NEWROOT" /sbin/init
halt_boot SWITCH_ROOT_FAILED
