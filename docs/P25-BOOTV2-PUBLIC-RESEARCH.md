# Public p25 AOSP boot-header-v2 research (unsigned)

This job produces **actual 33,554,432-byte output** with a standard AOSP
boot-v2 header from a real source-built ARM64 Linux Image.gz and DTB built by
the same public Kbuild tree. A separate verifier reopens and checks the bytes.

- Android boot v2, 1660-byte header in a 2048-byte page; sections are
  2048-byte aligned, unused p25 tail is zero-filled.
- Standard Android image ID is the AOSP SHA-1 content/size format field only;
  the real integrity receipt uses full image and component SHA-256.
- CI metadata is **synthetic-research-only**: zero physical addresses, empty
  cmdline, no MediaTek vendor64 wrapper, no LK header acceptance.
- Output is a **research candidate**; NOT an Air6-ready-to-sign, device
  bootable, licensed-for-distribution or flashable firmware.
- Genuine device acceptance still requires verified load addresses,
  vendor64/DTB semantics, signature boundary, provenance and LK checks.
- Never put unsigned binary bytes into public Actions artifacts, shared
  caches, Releases, registries or this Git history. CI files stay ephemeral;
  the SHA/readback log does NOT establish durable custody.

The implementation follows publicly documented *facts* of AOSP formatting,
not private implementation code:
- https://source.android.com/docs/core/architecture/bootloader/boot-image-header
- https://source.android.com/docs/core/architecture/bootloader/dtb-images
- https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/heads/android16-qpr2-release/include/bootimg/bootimg.h

The CI candidate does not reuse OEM LK headers, proprietary binaries, signing
keys, firmware, calibration data or device-unique payloads. Its source and
rights review are pending until independently approved.
