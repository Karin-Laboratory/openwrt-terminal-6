# PR #131 initial native P26/P44 CPIO proof (2026-11-09 UTC)

The first completed Native Actions run with the new alternative p26/P44 boot
CPIO built the **actual** 134,217,728-byte OpenWrt p26 from 37 installed packages,
produced an alternative CPIO directly from the same rootfs and independently
reopened and verified the full newc entries and complete padded p26 bytes.
The run also manufactured and independently read back its 33,554,432-byte
Android-v2 research p25 and booted its **separate known QEMU initramfs** with
procd/netifd. The alternative CPIO was **NOT booted**, and no binary survived
job cleanup.

- [Verbatim original UTC stdout excerpts](2026-11-09-pr131-native-p26-p44-readback.log)
- [Machine-verifiable SHA/source receipt](2026-11-09-pr131-native-p26-p44-receipt.json)
- [Successful Native Actions run](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/42536886682)
- [Exact source snapshot](https://github.com/Karin-Laboratory/openwrt-terminal-6/tree/8b1eb6266203e3d10c01624dce23eef27ebaa0e7)

Full p25 SHA-256: `d78f099248b3f87dbf13bb84e4149a65ccf7aa3eb19d40c4f4ad436d2ebe76b4` (32MiB; research synthetic header, not sign-ready)

Full p26 SHA-256: `2858fcfb866ee3243142a27c4ef6de7249f86e6b2aec262e063c46890486b2a5` (128MiB; real OpenWrt source-built rootfs)

Alternative CPIO SHA-256: `7cc5c1aac9b489df9d24a4476d830ca95d832116b0b8a0f5c0aebeafe559fca9` (independent readback PASS; **not executed**)

This source snapshot **precedes** the later RAM-only by-default /init, true
XZ/EXT4/OverlayFS Kbuild admission and target BusyBox smoke. Their success
requires separate CI evidence. No private keys, OEM headers, device-specific
calibration, signed images, firmware distributions or hardware operations
were involved. Source evidence is kept while this Git commit remains reachable;
merge and owner-controlled backup are advised.
