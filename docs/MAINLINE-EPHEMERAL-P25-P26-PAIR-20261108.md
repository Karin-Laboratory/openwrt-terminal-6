# Mainline same-run unsigned p25/p26 engineering pair (2026-11-08)

This integration reuses PR #127's real OpenWrt package/install root,
128MiB SquashFS p26 packer and independent full-byte/filesystem verifier.
After the same native OpenWrt kernel is relinked with procd PID1, the job
compresses the actual ARM64 Image and uses a same-Kbuild public DTB for a
separately verified 33,554,432-byte AOSP boot v2 research candidate.

The host job prints both SHA-256s from one run, after independently reading
the complete p26 and the separate-process p25. No artifacts, binary caches,
public releases, upload actions, credentials, signing, device access,
or flash operations are part of the workflow.

Acceptance boundary:
- 128MiB p26: actual real OpenWrt rootfs package install, SquashFS image,
  independent full-byte/filesystem readback. License clearance and Air6
  device boot remain pending.
- 32MiB p25: genuine bytes from source-built compressed Image and DTB,
  AOSP header v2 layout (1660B header, 2048B page), independent readback.
  Header uses synthetic zero load addresses and lacks manufacturer-specific
  vendor64 semantics. It is not sign-ready or accepted by LK.
- Both images exist only during the CI job, not in durable storage.
  Log SHA evidence is NOT preserved image bytes.
- Neither signature, real device boot, rights nor release is approved.

Format references:
https://source.android.com/docs/core/architecture/bootloader/boot-image-header
https://source.android.com/docs/core/architecture/bootloader/dtb-images

No private implementation source was copied. Historical experiments supplied
only factual engineering measurements, not restricted code or payloads.
