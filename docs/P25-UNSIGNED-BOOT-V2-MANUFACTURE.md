# Public unsigned P25 boot-v2 manufacture

This independently authored packer emits a fixed 32 MiB unsigned P25-shaped image. It performs no signing, flashing, boot-control changes, or device operations. Layout validation is not a boot-compatibility claim.

## Evidence and profile boundary

The private RC14 manufacturing record describes a built-in initramfs in the Linux kernel and a zero-length external ramdisk in the boot header. Its later runtime records report C-unit Slot A running Linux 6.18.44 with P26/P44 mounted, and owner-performed recovery/reboot checks. An earlier cold-boot record reports fallback to Slot B, so the evidence is not a clean, single-pass cold-boot success. Those records concern a private build and are not proof that this public source build boots.

The sanitized RC14 header observation is: Android magic, header version 2, page size 2048, OS version field `0x00020000`, board name `mt6990`, external ramdisk size 0, second-stage size 0, header size 1660, DTB section size 148829, and cmdline `bootopt=64S3,32N2,64N2 init_debug=4`. Observed address fields were kernel=0, tags=0, ramdisk=`0x01000000`, second=`0x00f00000`, and DTB=`0x01f00000`. Treat these as observed bytes from that RC14 image; they do not by themselves establish runtime physical placement or applicability to a different kernel/DTB.

The private image has a 64-byte opaque prefix before the FDT in its DTB section. Its semantics and lawful redistribution status are not established. No prefix bytes or hash from the private image are included here. A public manufacture invocation must provide an independently approved, locally held prefix and its SHA-256 in the explicit configuration. Without that exact input, the public P25 gate stops.

AOSP's generic v2 specification describes nonempty kernel, ramdisk, and DTB sections and page-aligned section layout ([boot image header](https://source.android.com/docs/core/architecture/bootloader/boot-image-header), [AOSP header definition](https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/heads/master/include/bootimg/bootimg.h)). The observed RC14 zero external ramdisk is therefore a vendor/LK-specific profile, not a generic AOSP-conformant profile. This repository labels it `kernel_embedded` and requires the empty external ramdisk explicitly; it does not imply that an arbitrary LK accepts that profile.

## Owner-private RC14 provenance and reference-profile gate

**2026-11-11 progress:** private RC13/RC14 source review confirms that the
64-byte prefix was **carried forward byte-for-byte** from an earlier owner-held
RC11 P25 template. It was not synthesized by the RC14 build algorithm.
Private RC8 assembler evidence shows `old_dtb[:64] + bare_dtb` after a
pinned template SHA check. This is evidence of *byte origin*, not permission
to redistribute or understanding of LK vendor-header semantics.

Two independently authored public audit utilities now separate these claims:

1. `tools/boot/audit_p25_reference_v2.py` operates **offline on an
   owner-held, SHA-pinned 32 MiB reference P25**. It validates the Android
   boot-v2 header, sizes and alignment, 64-byte FDT offset, bare DTB
   totalsize, boot ID, observed addresses and embedded-ramdisk layout.
   Optionally it compares an **independently provided local** 64-byte prefix.
   It never writes or extracts that prefix and writes a new 0600 JSON receipt
   only to an owner-selected private path.
2. `tools/boot/verify_p25_profile_provenance.py` independently checks
   candidate config fields and private prefix hash against the above
   receipt, and validates the newly built public DTB container. It reports
   whether the public DTB differs from the reference bare DTB.
   **Matching prior bytes does not validate memory placement, the new public
   DTB, LK acceptance or redistribution rights.**

Run these in an **owner-controlled local workspace**, not a public CI
environment with confidential image or prefix inputs:

```sh
python3 tools/boot/audit_p25_reference_v2.py \
  --reference /OWNER_PRIVATE/p25-reference.img \
  --expected-sha256 '<owner-verified-full-reference-sha256>' \
  --candidate-prefix /OWNER_PRIVATE/observed-prefix.bin \
  --private-receipt /OWNER_PRIVATE/first-unused/reference-audit.json

python3 tools/boot/verify_p25_profile_provenance.py \
  --config /OWNER_PRIVATE/boot-v2-config.json \
  --prefix /OWNER_PRIVATE/observed-prefix.bin \
  --audit-receipt /OWNER_PRIVATE/first-unused/reference-audit.json \
  --public-dtb /OWNER_PRIVATE/public-built/mt6990-air-terminal-6.dtb
```

The native unsigned P25 build now requires all **three** explicit inputs
(`SBAT6_P25_BOOT_V2_CONFIG`, `SBAT6_P25_DTB_SECTION_PREFIX`,
`SBAT6_P25_REFERENCE_AUDIT`); otherwise it emits a named BLOCKED
reason and creates no P25. No reference P25, prefix, or owner receipt is
ever added to this repository or uploaded as a CI artifact.

**Separate unresolved authorizations:** a lawful/independently created
prefix or documented permission to use the old one, independent validation
that the observed load addresses and DTB suit the new public kernel, actual
LK acceptance and device boot, and rights clearance for any distribution.
A successful metadata audit must *not* be labeled a flashable pair.

## Inputs and command

The config is an exact JSON object with these keys:

```json
{
  "kernel_addr": "0x0",
  "ramdisk_addr": "0x01000000",
  "second_addr": "0x00f00000",
  "tags_addr": "0x0",
  "dtb_addr": "0x01f00000",
  "page_size": 2048,
  "os_version": 131072,
  "name": "mt6990",
  "cmdline": "bootopt=64S3,32N2,64N2 init_debug=4",
  "ramdisk_mode": "kernel_embedded",
  "dtb_prefix_bytes": 64,
  "dtb_prefix_sha256": "<approved-local-input-sha256>"
}
```

The values shown reflect the sanitized RC14 observation. They are **not a validated configuration for the public kernel or board DTB**. Do not use this example as a manufacturing approval. The prefix digest placeholder is intentionally not an input value.

```sh
python3 tools/boot/pack_p25_unsigned_v2.py \
  --kernel /private/build/Image.gz \
  --ramdisk /private/build/empty-ramdisk \
  --dtb /private/build/board.dtb \
  --dtb-prefix /private/approved/dtb-section-prefix \
  --config /private/validated/boot-v2-config.json \
  --output /private/build/unsigned-p25.img
```

The packer checks the gzip stream and that its decompressed bytes are an ARM64 Image, validates the FDT header/total size, config schema, prefix length/hash, section sizes/alignment/bounds, 32 MiB output and zero tail. `tools/boot/verify_p25_independent.py` independently reads the complete output back and checks the header, configuration, sections, prefix, boot ID and padding.

## Embedded initramfs check

The native kernel build links the first-stage CPIO into `usr/initramfs_data.o` and `vmlinux`. `tools/boot/verify_kernel_initramfs.py` verifies the input `.init.ramfs` section in `usr/initramfs_data.o`, then uses `__initramfs_start` and the address of the 64-bit `__initramfs_size` payload to locate and compare the exact bytes folded into vmlinux `.init.data`. The linked ELF may report `st_size=0` for this assembly-defined size symbol, so the verifier validates the containing allocated section and reads exactly eight bytes at the symbol address instead of treating ELF symbol-size metadata as payload size. It decompresses those bytes to the expected CPIO, checks that the section occurs once in the ARM64 Image, and confirms the supplied gzip kernel decodes byte-for-byte to that Image. This proves source-build linkage and input identity, not that LK inflates or executes it on hardware.

## Same-run P25/P26 gate and CI

A matching same-run P25/P26 pair receipt is generated only if the caller provides `SBAT6_P25_BOOT_V2_CONFIG`, `SBAT6_P25_DTB_SECTION_PREFIX`, and `SBAT6_P25_REFERENCE_AUDIT` as coherent local inputs. Neither is committed or stored as a repository secret. CI does not upload images, receipts containing private values, or firmware artifacts. If either input is absent, CI records an explicit P25 block reason and emits no P25 or pair receipt; P26 manufacture/readback is independent.

The pair verifier checks the full 32 MiB P25 and 128 MiB P26 identities, producer and independent P26 readback receipts, exact P26 SHA-256 embedded in the verified CPIO, and the CPIO linkage to the built kernel. The receipt is an unsigned byte-identity result only.

`tests/test_p44_real_ext4.sh` exercises P44 state logic on newly created temporary ext4 image files. It checks empty initialization, preservation of a recognized overlay, resume of the exact recognized interrupted state, unchanged stop on unknown data, remount persistence, and inert behavior of the optional late extension hook without an enable marker. It does not touch any physical partition. This root-only integration test is run locally, not from GitHub Actions, because the repository's workflow policy disallows privileged shell steps. It requires e2fsprogs, loop mounts and a private mount namespace; it refuses to run the disabled-hook test if host `/overlay` already exists or is mounted.

## Remaining gates

- The sanitized RC14 header observations do not validate addresses/cmdline against the separately built public kernel and DTB.
- The opaque DTB-section prefix must be sourced/authorized and independently validated by the image owner; it is not present in this repository.
- Public board DTB compatibility, LK parsing/inflate acceptance, real memory placement and first-stage execution remain unproven.
- No public P25 candidate or P25/P26 pair can be manufactured until the validated configuration and prefix inputs are supplied to an owner-controlled run.
- No signing, physical boot, distribution-rights approval or device installation is performed here.

A P26 source build/readback, a P25 byte-layout check, and an actual Air Terminal 6 boot are separate claims and must be reported separately.
