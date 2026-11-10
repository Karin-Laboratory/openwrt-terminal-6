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


## Observed serial transcript, ordering, and fail-closed corruption

`tools/boot/check_qemu_p26_ram_boot.py` is an **independent** source-only
serial-log validator with three explicit modes: missing P26 (no virtual block
attached), SHA mismatch (a one-bit modified ephemeral P26 copy), and positive
RAM-overlay boot. It accepts a mode only if the actual serial log contains
exactly one kernel `Run /init as init process` marker and all mode-specific
stages in strict order. It rejects duplicates, missing procd, incorrect
transition order, panic, unexpected blockers and impossible post-rejection
stages. Positive mode also independently re-hashes the full original
128MiB P26 and verifies its original same-run receipt.

Native CI logs are captured to transient files and separately inspected by
this parser. The negative QEMU corruption test flips one bit in a temporary
**copy** of the P26 and attaches the copy **read-only** under QEMU. The original
P26 and CPIO remain unchanged. The expected result is
`AIR6_BOOT_BLOCKED_P26_SHA_MISMATCH`, before any writable mount or
`switch_root`. The positive QEMU acceptance additionally requires a procd
early-start log *after* `switch_root` begins. None of these are treated as
Air6 hardware acceptance, and passing source unit tests is not itself
runtime success.

## Same-run alternative initramfs research P25 (2026-11-10)

The native build now attempts a **second, separate unsigned research P25**
after compiling the actual alternative-initramfs kernel Image. Unlike the
original QEMU/procd P25, this Image contains the P26-hash-aware `/init`
and is compressed with `gzip -n` before boot-v2 packing.

The CI reuses the *same* synthetic AOSP-v2 metadata and same compiled
Air6 DTB, independently verifies the 32MiB P25 byte layout and checks its
pair receipt against the same-run source-built 128MiB P26 and the alternative
CPIO's embedded P26 SHA. This catches packaging/pairing drift without
disclosing or consuming any owner-only device metadata.

**Limits:** This check is not a proof that LK can authenticate, parse or
inflate the image. The P25 still has zero synthetic load addresses, lacks
confirmed OEM vendor64 semantics and is neither signer-ready nor flashable.
The alternative Air6 initramfs is not interchangeable with the QEMU-only
virtio variant. A green CI here is an engineering artifact, not hardware
boot evidence. All generated images remain ephemeral.

## Optional external 64-byte-prefixed FDT section support

The public boot-v2 research packer now accepts an **externally supplied**
64-byte-prefixed FDT *section* when its metadata explicitly sets
`dtb_layout=opaque-64-prefix-plus-fdt` and a matching
`vendor64_prefix_sha256`. The builder validates the prefix hash and the
inner FDT header/size; the independent reader repeats those checks against
the packed 32MiB P25. The default remains the original bare FDT layout.

This enables private experiments with an independently reviewed, lawfully
obtained section without adding OEM bytes, device identifiers or proprietary
prefix-generation recipes to the public repository. Tests use a synthetic
64-byte prefix only. The 64-byte boundary and SHA **do not establish the
meaning of the prefix, load-address correctness, or LK acceptance**.
No vendor64 sample is shipped or assumed. The current public CI research P25
continues to pack a bare FDT.
