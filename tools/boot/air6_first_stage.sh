#!/bin/sh
# SPDX-License-Identifier: MIT
# Public, independently authored experimental Air6 p26/p44 first-stage handoff.
# Fail closed without formatting or repairing existing persistent partitions.
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
fail() {
    echo "AIR6_FIRST_STAGE_BLOCKED_$1" >/dev/console 2>/dev/null || :
    # PID1 must never exit on a partially initialized device.
    while :; do sleep 60; done
}
[ "$$" -eq 1 ] || fail NOT_PID1
mount -t proc proc /proc || fail PROC
mount -t sysfs sysfs /sys || fail SYS
mount -t devtmpfs devtmpfs /dev || fail DEVTMPFS
grep -qw 'bootslot=a' /proc/cmdline || fail NOT_SLOT_A
root=/dev/mmcblk0p26
persist=/dev/mmcblk0p44
# devtmpfs can mount before the eMMC partition nodes have appeared.
# Wait at most 20 seconds; never create, repair, or write partition nodes.
i=0
while [ ! -b "$root" ] || [ ! -b "$persist" ]; do
    [ "$i" -lt 20 ] || fail PARTITIONS_NOT_BLOCK
    sleep 1
    i=$((i + 1))
done
[ "$root" != "$persist" ] || fail PARTITIONS_ALIASED
[ -r /sys/class/block/mmcblk0p26/uevent ] &&
    grep -qx 'PARTNAME=rootfs_a' /sys/class/block/mmcblk0p26/uevent ||
    fail P26_PARTNAME
[ -r /sys/class/block/mmcblk0p44/uevent ] &&
    grep -qx 'PARTNAME=rootfs_data' /sys/class/block/mmcblk0p44/uevent ||
    fail P44_PARTNAME
/usr/libexec/air6/verify-bound-p26 /etc/air6/p26.sha256 "$root" || fail P26_SHA
echo 'AIR6_FIRST_STAGE_P26_SHA_PASS' >/dev/console
mkdir -p /mnt/air6/rom /mnt/air6/check /mnt/air6/rw /mnt/air6/newroot || fail MOUNTPOINTS
mount -t squashfs -o ro "$root" /mnt/air6/rom || fail ROM
[ -x /mnt/air6/rom/sbin/init ] || fail ROM_INIT
# Read-only and no journal replay: never mutate owner's ext4 during validation.
mount -t ext4 -o ro,noload "$persist" /mnt/air6/check || fail P44_READONLY
/usr/libexec/air6/prepare-p44-state /mnt/air6/check check
p44_state=$?
case "$p44_state" in
    0) p44_initial_state=ready ;;
    2) p44_initial_state=empty ;;
    3) p44_initial_state=transaction ;;
    *) fail P44_READONLY_STATE ;;
esac
echo 'AIR6_FIRST_STAGE_P44_READONLY_PREFLIGHT_PASS' >/dev/console
umount /mnt/air6/check || fail P44_CHECK_UNMOUNT
echo 'AIR6_FIRST_STAGE_P44_PREFLIGHT_PASS' >/dev/console
mount -t ext4 -o rw,noatime,nosuid,nodev "$persist" /mnt/air6/rw ||
    fail P44_RW
if [ "$p44_initial_state" = empty ] || [ "$p44_initial_state" = transaction ]; then
    /usr/libexec/air6/prepare-p44-state /mnt/air6/rw init ||
        fail P44_EMPTY_INITIALIZATION
else
    /usr/libexec/air6/prepare-p44-state /mnt/air6/rw check ||
        fail P44_STATE_CHANGED
fi
mount -t overlay overlay -o lowerdir=/mnt/air6/rom,upperdir=/mnt/air6/rw/upper,workdir=/mnt/air6/rw/work /mnt/air6/newroot ||
    fail ROOT_OVERLAY
[ -x /mnt/air6/newroot/sbin/init ] || fail OVERLAY_INIT
mkdir -p /mnt/air6/newroot/rom /mnt/air6/newroot/overlay ||
    fail NEWROOT_DIRS
mount -o bind /mnt/air6/rw /mnt/air6/newroot/overlay || fail P44_BIND
mount -t squashfs -o ro "$root" /mnt/air6/newroot/rom || fail ROM_READONLY
echo 'AIR6_FIRST_STAGE_SWITCH_ROOT_BEGIN' >/dev/console
export INITRAMFS=1
exec /sbin/switch_root -c /dev/console /mnt/air6/newroot /sbin/init
fail SWITCH_ROOT
