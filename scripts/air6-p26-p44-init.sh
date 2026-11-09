#!/bin/sh
# SPDX-License-Identifier: MIT
# Experimental Air6 /init: RAM-only overlay by default; P44 requires owner approval.
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
        P26_RAM_OVERLAY_DEFAULT P44_EXT4_RO_NOLOAD P44_EXPLICIT_RW_GO \
        OVERLAYFS SWITCH_ROOT NO_AUTO_RECOVERY
    exit 0
fi
[ "$#" -eq 0 ] || exit 2
[ "$$" -eq 1 ] || halt_boot NOT_PID1
log RAM_INIT_ENTER

P26=/dev/mmcblk0p26
P44=/dev/mmcblk0p44
ROM=/mnt/air6-rom
UPPER=/mnt/air6-p44
RAM=/mnt/air6-tmpfs
NEWROOT=/mnt/air6-newroot
EXPECTED=/etc/air6-p26.sha256
P44_PARTNAME=/etc/air6-p44.partname
OWNER_GO=/etc/air6-owner-p44-rw-go

# Mount pseudo-filesystems first, then inspect actual device nodes and GPT.
mkdir -p /proc /sys /dev "$ROM" "$NEWROOT" ||
    halt_boot MOUNTPOINT_CREATE
mount -t proc proc /proc || halt_boot PROC_MOUNT
mount -t sysfs sysfs /sys || halt_boot SYS_MOUNT
mount -t devtmpfs devtmpfs /dev || halt_boot DEV_MOUNT

[ -b "$P26" ] || halt_boot P26_NOT_BLOCK
grep -qx 'PARTNAME=rootfs_a' /sys/class/block/mmcblk0p26/uevent ||
    halt_boot P26_GPT_PARTNAME

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
[ -x "$ROM/sbin/procd" ] && [ -f "$ROM/etc/preinit" ] &&
    [ ! -L "$ROM/etc/preinit" ] ||
    halt_boot P26_INIT_PREINIT_MISSING
log P26_ROM_MOUNT_PASS

# Default is *volatile*: no P44 open, mount, journal replay or writes.
# To opt in to P44, a separately provisioned owner consent file is required.
if [ ! -e "$OWNER_GO" ] && [ ! -L "$OWNER_GO" ]; then
    mkdir -p "$RAM" || halt_boot RAM_MOUNTPOINT
    mount -t tmpfs -o mode=0700,size=64m,nosuid,nodev tmpfs "$RAM" ||
        halt_boot RAM_TMPFS_MOUNT
    mkdir -p "$RAM/upper" "$RAM/work" || halt_boot RAM_WORKDIR_CREATE
    BACKING="$RAM"
    log P26_RAM_OVERLAY_DEFAULT
else
    # Existing approval path: unknown or malformed owner consent halts.
    [ -f "$OWNER_GO" ] && [ ! -L "$OWNER_GO" ] ||
        halt_boot P44_RW_NOT_APPROVED
    [ "$(cat "$OWNER_GO" 2>/dev/null)" = AIR6_P44_RW_OWNER_APPROVED_FOR_THIS_PAIR ] ||
        halt_boot P44_RW_TOKEN_NOT_MATCHED
    [ -b "$P44" ] || halt_boot P44_NOT_BLOCK
    [ -s "$P44_PARTNAME" ] && [ ! -L "$P44_PARTNAME" ] ||
        halt_boot P44_PARTNAME_UNREVIEWED
    read -r partname < "$P44_PARTNAME" || halt_boot P44_PARTNAME_UNREADABLE
    case "$partname" in
        ''|*[!a-zA-Z0-9_-]*) halt_boot P44_PARTNAME_INVALID ;;
    esac
    grep -qx "PARTNAME=$partname" /sys/class/block/mmcblk0p44/uevent ||
        halt_boot P44_GPT_PARTNAME
    mkdir -p "$UPPER" || halt_boot P44_MOUNTPOINT
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
    # Journal replay must not silently invalidate the read-only preflight.
    [ -d "$UPPER/upper" ] && [ ! -L "$UPPER/upper" ] &&
        [ -d "$UPPER/work" ] && [ ! -L "$UPPER/work" ] ||
        halt_boot P44_POST_JOURNAL_LAYOUT
    [ ! -e "$UPPER/upper/etc/preinit" ] &&
        [ ! -L "$UPPER/upper/etc/preinit" ] &&
        [ ! -e "$UPPER/upper/sbin/init" ] &&
        [ ! -L "$UPPER/upper/sbin/init" ] ||
        halt_boot P44_POST_JOURNAL_BOOT_SHADOW
    BACKING="$UPPER"
    log P44_OWNER_APPROVED
fi
mount -t overlay overlay -o "lowerdir=$ROM,upperdir=$BACKING/upper,workdir=$BACKING/work" \
    "$NEWROOT" || halt_boot P44_OVERLAY_MOUNT_FAILED
[ -f "$NEWROOT/etc/preinit" ] && [ ! -L "$NEWROOT/etc/preinit" ] &&
    [ -x "$NEWROOT/sbin/procd" ] && [ -x "$NEWROOT/sbin/init" ] ||
    halt_boot OVERLAY_BOOT_FILES_MISSING
# A symlinked /sbin/init can resolve relative to the WRONG root. Compare
# link text and actual procd object within each explicitly rooted tree.
cmp -s "$ROM/etc/preinit" "$NEWROOT/etc/preinit" ||
    halt_boot OVERLAY_PREINIT_CONTENT_CHANGED
if [ -L "$ROM/sbin/init" ]; then
    [ -L "$NEWROOT/sbin/init" ] ||
        halt_boot OVERLAY_INIT_LINK_TYPE
    original_link="$(readlink "$ROM/sbin/init")" ||
        halt_boot ROM_INIT_LINK_READ
    merged_link="$(readlink "$NEWROOT/sbin/init")" ||
        halt_boot OVERLAY_INIT_LINK_READ
    [ "$original_link" = "$merged_link" ] ||
        halt_boot OVERLAY_INIT_LINK_CHANGED
    case "$original_link" in
        procd|sbin/procd|/sbin/procd) : ;;
        *) halt_boot OVERLAY_INIT_LINK_UNREVIEWED ;;
    esac
else
    [ ! -L "$NEWROOT/sbin/init" ] ||
        halt_boot OVERLAY_INIT_LINK_INJECTED
    cmp -s "$ROM/sbin/init" "$NEWROOT/sbin/init" ||
        halt_boot OVERLAY_INIT_CONTENT_CHANGED
fi
cmp -s "$ROM/sbin/procd" "$NEWROOT/sbin/procd" ||
    halt_boot OVERLAY_PROCD_BINARY_CHANGED
log OVERLAY_MOUNT_PASS

mkdir -p "$NEWROOT/rom" "$NEWROOT/overlay" \
    "$NEWROOT/proc" "$NEWROOT/sys" "$NEWROOT/dev" ||
    halt_boot NEWROOT_MOUNTPOINT
mount --move "$ROM" "$NEWROOT/rom" || halt_boot MOVE_ROM
mount --move "$BACKING" "$NEWROOT/overlay" || halt_boot MOVE_OVERLAY_BACKING
mount --move /proc "$NEWROOT/proc" || halt_boot MOVE_PROC
mount --move /sys "$NEWROOT/sys" || halt_boot MOVE_SYS
mount --move /dev "$NEWROOT/dev" || halt_boot MOVE_DEV
log SWITCH_ROOT_BEGIN
exec switch_root -c /dev/console "$NEWROOT" /sbin/init
halt_boot SWITCH_ROOT_FAILED
