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
length, nonempty components, output size and load-address shape. Unit tests
exercise the synthetic layout only.


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
proven separately. Do not treat the synthetic layout gate as an RK14/RC14 boot
reproduction.

## Acceptance still pending

1. An independently verified public-source ARM64 kernel, correct C-unit DTB
   and real OpenWrt initramfs, plus verified build receipts.
2. Observed RC14-compatible load addresses, boot arguments and vendor-specific
   kernel/DTB ABI, obtained through lawful documented observations.
3. Independent parser/readback of all 32 MiB, zero padding, section offsets,
   hashes and output identity on the exact manufactured candidate.
4. LK parsing and **physical** A-slot boot validation. Android v2 structure alone
   does not establish Air6 LK acceptance, successful inflate, init/PID1 or network.
5. A matching p26 rootfs with independently checked full 128 MiB byte layout.

P25 is **not** a signed, tested or deployable Air Terminal 6 image at this stage.
Neither a synthetic unit-test PASS nor a source-built candidate is a boot claim.

Provenance: MIT independently authored assembly and tests. Android's format
description is used as an interface specification, not copied source code.
