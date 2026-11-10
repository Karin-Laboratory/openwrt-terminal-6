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
# Manufacturer-selected, immutable initramfs mode. The optional RAM path
# remains research-only; RC14-style persistent boot requires an explicit
# second build of the P44-required variant, never a runtime fallback.
BOOT_MODE='ram-experimental'
case "$BOOT_MODE" in
    ram-experimental|p44-required) : ;;
    *) halt_boot UNRECOGNIZED_BOOT_MODE ;;
esac

# Mount pseudo-filesystems first, then inspect actual device nodes and GPT.
mkdir -p /proc /sys /dev "$ROM" "$NEWROOT" ||
    halt_boot MOUNTPOINT_CREATE
mount -t proc proc /proc || halt_boot PROC_MOUNT
mount -t sysfs sysfs /sys || halt_boot SYS_MOUNT
mount -t devtmpfs devtmpfs /dev || halt_boot DEV_MOUNT
# Private RC13/14 ran exclusively from A. Never mount A's P26/P44 from a
# stock-B boot or any ambiguous kernel command line.
grep -qw 'bootslot=a' /proc/cmdline || halt_boot NOT_SLOT_A

# RC15 research portability path: locate both partitions by GPT PARTNAME
# rather than inheriting one C-unit's eMMC numbering. Reject duplicates
# and cross-disk aliases before mounting or writing any filesystem.
if [ "$BOOT_MODE" = p44-required ]; then
    # Private RC13 allowed up to 20 seconds for eMMC/GPT enumeration.
    # Repeat ONLY read-only sysfs scans; duplicate labels fail immediately.
    # Never infer "missing partition" from one transient early scan.
    scan_attempt=0
    while [ "$scan_attempt" -lt 80 ]; do
        found_p26=
        found_p44=
        found_userdata=
        for entry in /sys/class/block/mmcblk*p*/uevent; do
            [ -f "$entry" ] || continue
            device="${entry%/uevent}"
            device="${device##*/}"
            case "$device" in mmcblk*p[0-9]*) : ;; *) continue ;; esac
            if grep -qx 'PARTNAME=rootfs_a' "$entry"; then
                [ -z "$found_p26" ] || halt_boot P26_DUPLICATE_GPT_PARTNAME
                found_p26="/dev/$device"
            fi
            if grep -qx 'PARTNAME=rootfs_data' "$entry"; then
                [ -z "$found_p44" ] || halt_boot P44_DUPLICATE_GPT_PARTNAME
                found_p44="/dev/$device"
            fi
            if grep -qx 'PARTNAME=user_data' "$entry"; then
                [ -z "$found_userdata" ] || halt_boot USER_DATA_DUPLICATE_GPT_PARTNAME
                found_userdata="/dev/$device"
            fi
        done
        if [ -n "$found_p26" ] && [ -b "$found_p26" ] &&
            [ -n "$found_p44" ] && [ -b "$found_p44" ] &&
            [ -n "$found_userdata" ] && [ -b "$found_userdata" ]; then
            break
        fi
        sleep 0.25
        scan_attempt=$((scan_attempt + 1))
    done
    [ -n "$found_p26" ] && [ -n "$found_p44" ] &&
        [ -n "$found_userdata" ] ||
        halt_boot REQUIRED_GPT_PARTITIONS_NOT_FOUND
    p26_disk="${found_p26%p[0-9]*}"
    p44_disk="${found_p44%p[0-9]*}"
    userdata_disk="${found_userdata%p[0-9]*}"
    [ -n "$p26_disk" ] && [ "$p26_disk" = "$p44_disk" ] &&
        [ "$p26_disk" = "$userdata_disk" ] ||
        halt_boot REQUIRED_GPT_CROSS_DISK
    # RC13 verified a preserved, preceding user_data partition. Use
    # observed partition-table geometry rather than C-unit sector constants.
    [ -b "$found_userdata" ] || halt_boot USER_DATA_NOT_BLOCK
    p44_name="${found_p44##*/}"
    userdata_name="${found_userdata##*/}"
    read -r p44_start < "/sys/class/block/$p44_name/start" ||
        halt_boot P44_START_UNREADABLE
    read -r p44_sectors < "/sys/class/block/$p44_name/size" ||
        halt_boot P44_SIZE_UNREADABLE
    read -r userdata_start < "/sys/class/block/$userdata_name/start" ||
        halt_boot USER_DATA_START_UNREADABLE
    read -r userdata_sectors < "/sys/class/block/$userdata_name/size" ||
        halt_boot USER_DATA_SIZE_UNREADABLE
    for count in "$p44_start" "$p44_sectors" "$userdata_start" "$userdata_sectors"; do
        case "$count" in ''|*[!0-9]*) halt_boot PARTITION_GEOMETRY_INVALID ;; esac
    done
    [ "$p44_sectors" -gt 0 ] && [ "$userdata_sectors" -gt 0 ] ||
        halt_boot EMPTY_PARTITION_GEOMETRY
    [ "$p44_start" -ge "$((userdata_start + userdata_sectors))" ] ||
        halt_boot P44_OVERLAPS_USER_DATA
    P26="$found_p26"
    P44="$found_p44"
fi
[ -b "$P26" ] || halt_boot P26_NOT_BLOCK
grep -qx 'PARTNAME=rootfs_a' "/sys/class/block/${P26##*/}/uevent" ||
    halt_boot P26_GPT_PARTNAME
# sysfs block sizes are 512-byte sectors. The p26 manufacturing contract
# is exactly 134,217,728 bytes, so reject a wrong-sized GPT target before
# streaming any partition bytes for the SHA gate.
read -r p26_sectors < "/sys/class/block/${P26##*/}/size" ||
    halt_boot P26_SIZE_UNREADABLE
[ "$p26_sectors" = 262144 ] || halt_boot P26_PARTITION_SIZE_MISMATCH

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
if [ "$BOOT_MODE" = ram-experimental ] &&
    [ ! -e "$OWNER_GO" ] && [ ! -L "$OWNER_GO" ]; then
    mkdir -p "$RAM" || halt_boot RAM_MOUNTPOINT
    mount -t tmpfs -o mode=0700,size=64m,nosuid,nodev tmpfs "$RAM" ||
        halt_boot RAM_TMPFS_MOUNT
    mkdir -p "$RAM/upper" "$RAM/work" || halt_boot RAM_WORKDIR_CREATE
    BACKING="$RAM"
    log P26_RAM_OVERLAY_DEFAULT
else
    # Manufacturing P44-required mode is opt-in at build time. It never
    # depends on a consent script preinstalled on P44 and never falls back
    # to volatile RAM. Initial P44 formatting/provisioning is a separate
    # owner-approved operation, never performed during boot.
    [ -b "$P44" ] || halt_boot P44_NOT_BLOCK
    if [ "$BOOT_MODE" = p44-required ]; then
        grep -qx 'PARTNAME=rootfs_data' "/sys/class/block/${P44##*/}/uevent" ||
            halt_boot P44_ROOTFS_DATA_GPT_MISMATCH
    else
        [ -f "$OWNER_GO" ] && [ ! -L "$OWNER_GO" ] ||
            halt_boot P44_RW_NOT_APPROVED
        [ "$(cat "$OWNER_GO" 2>/dev/null)" = AIR6_P44_RW_OWNER_APPROVED_FOR_THIS_PAIR ] ||
            halt_boot P44_RW_TOKEN_NOT_MATCHED
        [ -s "$P44_PARTNAME" ] && [ ! -L "$P44_PARTNAME" ] ||
            halt_boot P44_PARTNAME_UNREVIEWED
        read -r partname < "$P44_PARTNAME" || halt_boot P44_PARTNAME_UNREADABLE
        case "$partname" in
            ''|*[!a-zA-Z0-9_-]*) halt_boot P44_PARTNAME_INVALID ;;
        esac
        grep -qx "PARTNAME=$partname" "/sys/class/block/${P44##*/}/uevent" ||
            halt_boot P44_GPT_PARTNAME
    fi
    mkdir -p "$UPPER" || halt_boot P44_MOUNTPOINT
    # Check P44 with journal replay disabled before owner-authorized RW mount.
    mount -t ext4 -o ro,noload "$P44" "$UPPER" ||
        halt_boot P44_RO_NOLOAD_MOUNT
    # RC13/14 observed a P44 ext4 marker and fstools state symlink.
    # Inspect only: no formatting, repair, or auto-provisioning here.
    marker="$UPPER/.sba6d-rootfs-data-v1"
    [ -f "$marker" ] && [ ! -L "$marker" ] ||
        halt_boot P44_MARKER_MISSING_OR_LINK
    grep -Fxq 'SBA6D_ROOTFS_DATA_V1' "$marker" ||
        halt_boot P44_MARKER_MISMATCH
    [ -L "$UPPER/.fs_state" ] ||
        halt_boot P44_FS_STATE_NOT_SYMLINK
    fs_state="$(readlink "$UPPER/.fs_state")" ||
        halt_boot P44_FS_STATE_UNREADABLE
    [ "$fs_state" = 2 ] || halt_boot P44_FS_STATE_NOT_READY
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
    mount -t ext4 -o rw,noatime,nosuid,nodev "$P44" "$UPPER" ||
        halt_boot P44_RW_MOUNT_FAILED
    # Journal replay must not silently invalidate the read-only preflight.
    [ -d "$UPPER/upper" ] && [ ! -L "$UPPER/upper" ] &&
        [ -d "$UPPER/work" ] && [ ! -L "$UPPER/work" ] ||
        halt_boot P44_POST_JOURNAL_LAYOUT
    # Recheck identity after the permitted RW mount/journal replay.
    [ -f "$UPPER/.sba6d-rootfs-data-v1" ] &&
        [ ! -L "$UPPER/.sba6d-rootfs-data-v1" ] &&
        grep -Fxq 'SBA6D_ROOTFS_DATA_V1' "$UPPER/.sba6d-rootfs-data-v1" ||
        halt_boot P44_POST_JOURNAL_MARKER_CHANGED
    [ -L "$UPPER/.fs_state" ] &&
        [ "$(readlink "$UPPER/.fs_state")" = 2 ] ||
        halt_boot P44_POST_JOURNAL_FS_STATE_CHANGED

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
# P44 must not replace/whiteout the verified, P26-internal management entry.
# This fails closed for RC15-like mode; RAM research boot is unchanged.
if [ "$BOOT_MODE" = p44-required ]; then
    management=usr/libexec/sba6d/rc14-management.sh
    [ -f "$ROM/$management" ] && [ ! -L "$ROM/$management" ] &&
        [ -x "$ROM/$management" ] || halt_boot P26_MANAGEMENT_ENTRY_ABSENT
    [ -f "$NEWROOT/$management" ] && [ ! -L "$NEWROOT/$management" ] &&
        [ -x "$NEWROOT/$management" ] || halt_boot P44_MANAGEMENT_ENTRY_SHADOW
    cmp -s "$ROM/$management" "$NEWROOT/$management" ||
        halt_boot P44_MANAGEMENT_ENTRY_REPLACED
fi
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
# Preserve RC13/14's proven handoff: 70_initramfs_test uses INITRAMFS=1
# to avoid a second fstools mount_root overlay transition in /etc/preinit.
export INITRAMFS=1
exec switch_root -c /dev/console "$NEWROOT" /sbin/init
halt_boot SWITCH_ROOT_FAILED
