# Air6 p26/P44 alternative /init bootstrap (public-source, not enabled)

This optional build produces an **actual newc CPIO** from the same native
OpenWrt package-install rootfs used for the 128MiB p26. It embeds the **full
same-run SHA-256** of that *whole padded p26* into
/etc/air6-p26.sha256 and a separately authored shell /init. A second Python
process independently reopens the CPIO, receipt, 128MiB input and ALL rootfs
files/links to check their bytes.

The currently successful QEMU procd PID1 boot initramfs is **not replaced**.
The new CPIO is **not embedded into the shipping candidate p25 or activated
by Kbuild**. No Air6 hardware first boot, mount, switch_root, Ethernet, SSH or
AP success follows from its successful construction and readback.

## Runtime design (not hardware accepted)

- Require PID1 and the real GPT p26=rootfs_a; only check the owner-provided P44 PARTNAME if persistent P44 mode is explicitly
  authorized (never guess a name).
- Default to a **64MiB tmpfs RAM upper/work OverlayFS**, with p26 as the
  read-only SquashFS lower layer. This mode does **not** inspect, mount or
  write P44. Changes are volatile and are lost on reboot.
- Switch to P44 persistent ext4 upper/work only with an explicit private
  owner P44 RW approval marker, deliberately absent in public CPIOs.
- Hash the complete 134,217,728-byte p26 block partition and compare to
  the embedded full SHA before any writable mount.
- Mount p26 read-only SquashFS; preflight P44 ext4 with ro,noload, verify
  upper/work are real directories and reject critical entrypoint whiteouts.
- Under separate authorization only, mount P44 RW, build OverlayFS and
  verify that merged /etc/preinit and /sbin/init match the p26 lower layer.
- Move pseudo filesystems into the merged root, then exec switch_root.
- On any failure, hold PID1 with a diagnostic marker, never reformat,
  rewrite rootfs, switch slots, reboot, or fall back automatically.

## Limits that still block physical use

The public builder embeds neither /etc/air6-p44.partname nor
/etc/air6-owner-p44-rw-go. Therefore the alternative CPIO selects the
**RAM-only, nonpersistent** OverlayFS mode by default. Only the P44 read-write
branch fails closed unless separately authorized. This is a source-only runtime
path, not an assertion of hardware boot.

The exact P44 GPT PARTNAME, journal/read-write acceptance and physical
OverlayFS compatibility are not proven by the source-only test. BusyBox
switch_root/grep/cmp/sha256sum/mount/umount/sleep must be checked against the
**actual AArch64 target binary**, not assumed from host BusyBox. Owner-private
approval must be bound to a particular unit/p25/p26/backup/rollback receipt
in a separate non-public procedure, not a generic checkbox.

Mounting P44 writable can replay its ext4 journal. No live device operation
is authorized by this source addition. The public CI runs the builder with
source-built package rootfs in scratch space only, discards its CPIO,
does not sign or upload it, and logs only SHA/acceptance boundaries.

Code: scripts/air6-p26-p44-init.sh,
tools/boot/build_p26_p44_initramfs.py,
tools/boot/verify_p26_p44_initramfs.py.

## QEMU virtio positive runtime gate (new, not Air6 hardware proof)

The native CI now creates a **separate synthetic QEMU-only newc archive**
derived from the same-run, independent-readback P26/P44 CPIO and **actual**
128MiB p26 SquashFS. The synthetic archive replaces exactly two p26 device
identifiers in `/init`: the hardware GPT path with `/dev/vda`, and the GPT
PARTNAME check with a virtio `DEVNAME=vda` identity check. All other archive
members and the embedded full p26 SHA remain byte-identical and are independently
verified by `tools/boot/verify_p26_qemu_virt_fixture.py`.

After the existing p25/p26 pair is manufactured and the known QEMU procd boot
is checked, CI compiles a **third** ephemeral kernel Image with the synthetic
newc, `CONFIG_VIRTIO_BLK=y` and `CONFIG_VIRTIO_MMIO=y`. QEMU's ARM64
`virt` machine receives the real unsigned 128MiB p26 as a **read-only**
virtio block device, with no NIC and no host device passthrough. The test
requires observed `/init` PID1, full p26 SHA verification, readonly p26
SquashFS mount, volatile RAM OverlayFS setup, actual `switch_root` and procd
startup. If any marker fails, the CI job fails rather than presenting QEMU
kernel boot as a positive rootfs acceptance.

This is a **new test with no successful result implied by its source code**.
It cannot establish Air6 MMC path/GPT compatibility, vendor64/LK boot acceptance,
P44 ext4 persistence, device-specific network hardware or signing. The
synthetic CPIO and virtual kernel are never used as p25 inputs and are never
published or uploaded. The original public production `/init` source is
never rewritten; only an ephemeral QEMU CPIO is patched.

