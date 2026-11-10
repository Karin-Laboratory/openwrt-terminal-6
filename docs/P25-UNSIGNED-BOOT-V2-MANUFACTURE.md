# Public, unsigned p25 boot-v2 manufacture

This is an **independently authored** host-side assembler based on the public Android
boot-image v2 specification:
https://source.android.com/docs/core/architecture/bootloader/boot-image-header

## Actual tool

`tools/boot/pack_p25_unsigned_v2.py` builds a precisely 33,554,432-byte unsigned
`boot_a` candidate (p25) with 4 KiB aligned header, gzip kernel, ramdisk
and FDT DTB; records SHA-256 receipt and a noncryptographic boot-image
SHA-1 ID. It does not sign, flash, change boot control or use OEM files.

```sh
python3 tools/boot/pack_p25_unsigned_v2.py \
  --kernel /private/build/Image.gz \
  --ramdisk /private/build/initramfs.cpio.gz \
  --dtb /private/build/board.dtb \
  --config /private/build/boot-v2-addresses.json \
  --output /private/build/unsigned-boot_a.p25
```

The caller must supply exactly `kernel_addr`, `ramdisk_addr`, `tags_addr`,
`dtb_addr`, `name` and `cmdline` in JSON. Numeric addresses are strings
(e.g. `"0x40080000"`); no device-specific values or confidential boot
parameters are provided by this repository. All supplied input files must
be lawfully sourced, independently built and checked before use.

The producer validates gzip framing and decompression, FDT header and total
length, nonempty components, output size and load-address shape. The independent
full-byte verifier now requires the **same explicit configuration** and checks
kernel/ramdisk/tags/DTB addresses, board name, the entire 1535-byte command
line, OS-version field, section bytes and zero padding. The verifier refuses
altered boot arguments even when section hashes still match. Synthetic tests
also corrupt the header and mutate config after manufacture. This is a byte
layout check, not confirmation the private RC14 LK accepts these values.


## Native source-built handoff (2026-11-10)

The native MT6990 package-build workflow now prepares three actual build inputs
after compiling the same kernel with the procd PID1 initramfs embedded:
`air6-native-Image.gz`, `air6-native-initramfs.cpio.gz`, and
`mt6990-air-terminal-6.dtb`. Compression uses `gzip -n -9` with no
source filename/timestamp; the job checks gzip integrity and prints SHA-256.

The workflow intentionally does not invent a kernel load address or boot
command line. Without `SBAT6_P25_BOOT_V2_CONFIG`, it emits
`P25_BLOCKED_RC14_COMPATIBLE_BOOT_V2_CONFIGURATION_UNAVAILABLE` and produces
no candidate p25. If an independently validated configuration file is available
to an isolated local/owner-controlled run, the same native inputs are passed
through the unsigned v2 assembler and **independent** full-32MiB verifier.
The public hosted job does not configure signing or upload the resulting image.

A native source-built Image with an embedded initramfs **and** a separate
ramdisk is an experimental handoff, not confirmation of the precise RC14 boot
protocol. The signed vendor-specific header extensions, LK inflate format
acceptance, real memory map, init transition and Air6 DTB compatibility must be
proven separately. Do not treat the synthetic layout gate as an RC14 boot
reproduction.

## Same-run unsigned P25/P26 pair identity

Once the real native P26 has passed independent 128 MiB extracted-tree readback,
and ONLY if independently validated owner-private boot-v2 address/config is
provided, the native job now builds an unsigned P25 and invokes
`tools/build/verify_unsigned_pair.py`. This tool independently rechecks P25
kernel/ramdisk/DTB, full 32 MiB layout and command-line/config identity,
rehashes the actual 128 MiB P26, and compares that hash with **both** the
P26 producer receipt and its separate independently verified readback
attestation. It requires matching SquashFS metadata and producer receipt
identity, then creates one exclusive-creation pair receipt.

The resulting `UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED` means the two candidate
images have consistent byte identity within the same native job, **not** that
either is signed, fits the device's proprietary boot extension, boots the Air6,
or has cleared distribution rights. Without an explicit accepted P25 config
the pair step is skipped/blocked, not silently represented by synthetic inputs.

## RC14-derived complete-P26 SHA binding (2026-11-10)

The private RC14 build evidence shows a critical dependency not covered by
standalone Android boot-v2 header packing: its first-stage initramfs was
regenerated to carry the **complete 128 MiB P26 SHA-256**. RC14 did not reuse
an earlier signed P25 after changing P26. This is an independently recorded
architectural observation, **not** imported private source or binary data.

The public native job now injects `etc/air6/p26.sha256` into the actual
procd initramfs from the exact newly manufactured P26 image, before the
kernel is rebuilt with `CONFIG_INITRAMFS_SOURCE`. The embedded file is a
`sha256sum -c`-compatible hash record referring to the P26 block device,
and a host-side check rejects missing/ambiguous SHA content. The final
independent unsigned-pair gate checks this same hash appears in the embedded
CPIO as well as the P26 producer and independent-readback receipts.

An independently authored full-P26 runtime checker
(`tools/boot/verify_bound_p26.sh`) is now also staged into the native
initramfs at `/usr/libexec/air6/verify-bound-p26`. It verifies a strict
hash record against the entire P26 device, fails closed on mismatch, missing
inputs or symlinked paths, and has host-only dynamic regression tests.
It never writes to the P26 device.

The earlier standalone procd test CPIO does not invoke this checker.
The separate experimental first-stage CPIO described below now does; the
full device boot path has not been tested. P44's late optional extension
runner remains independent.

## Source-built RC14-style first-stage path (experimental)

The public build now separately creates a **minimal AArch64 first-stage CPIO**
with `tools/build/build_air6_first_stage.py`, using the native OpenWrt
BusyBox + associated musl runtime, independently authored
`tools/boot/air6_first_stage.sh` as `/init`, the standalone full-P26
SHA checker and a fresh hash of the **same native P26**. There is no private
initramfs, RC14 shell code, OEM DTB or vendor blob in this new source.

The new `/init` is an experimental, fail-closed handoff:
1. Mount proc/sys/dev, check A slot and expected block devices.
2. Validate complete P26 SHA-256 before attempting P44 RW access.
3. Mount P26 SquashFS read-only, and check pre-existing P44 ext4 with
   `ro,noload`: marker text, `upper`/`work` directories and `.fs_state`
   symlink. No formatting, partitioning, repair or provisioning.
4. Only after the read-only gate, mount P44 RW, construct overlay lower/upper
   and work, expose `/rom` and `/overlay`, then `switch_root` to
   P26's `/sbin/init`.

The native job now **keeps its existing procd/QEMU smoke Image separate**.
After that test it builds a second MT6990 Image using the above first-stage
CPIO. It explicitly requires kernel built-ins for ext4, SquashFS XZ,
overlayfs and MMC block (no late module-loading dependency). A caller-supplied
validated boot-v2 header config is still required for final unsigned P25
packing and same-run P25/P26 pair identity confirmation.

Safety tests cover CPIO creation, missing/modified P26 input, non-AArch64
BusyBox, unsafe loader symlinks, first-stage shell syntax and SHA-before-P44
ordering. These host tests **cannot** prove target BusyBox applet availability,
MT6990 storage driver bring-up, DTB/LK compatibility or hardware boot. The
public P26 still lacks RC14's optional UART shell mode, and its network/SSH
startup is not verified. Neither image is approved for physical flashing.

## Acceptance still pending

1. An independently verified public-source ARM64 kernel, correct C-unit DTB
   and real OpenWrt initramfs, plus verified build receipts.
2. Observed RC14-compatible load addresses, boot arguments and vendor-specific
   kernel/DTB ABI, obtained through lawful documented observations.
3. Independent parser/readback of all 32 MiB, zero padding, section offsets,
   hashes, config-provided boot addresses/cmdline and output identity on the
   exact manufactured candidate.
4. LK parsing and **physical** A-slot boot validation. Android v2 structure alone
   does not establish Air6 LK acceptance, successful inflate, init/PID1 or network.
5. A matching p26 rootfs with independently checked full 128 MiB byte layout.

P25 is **not** a signed, tested or deployable Air Terminal 6 image at this stage.
Neither a synthetic unit-test PASS nor a source-built candidate is a boot claim.

Provenance: MIT independently authored assembly and tests. Android's format
description is used as an interface specification, not copied source code.
