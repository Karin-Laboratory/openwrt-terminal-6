# OpenWrt integration workstream (source only)

This directory is a *pre-integration* track, not a board profile or firmware builder. The Linux v6.18 RFC patches may only be applied to the exact pinned upstream blobs. An arbitrary OpenWrt patchset or kernel version must **not** be silently treated as compatible. See `scripts/apply-public-rfc-series.sh` for the hash-checked source gate.

Milestones: obtain independently reviewed SBAT6D board DTS; identify exact OpenWrt kernel target/version; compare MediaTek Ethernet C/header blob IDs; rebase patches if needed; build modules and full kernel in public CI; verify rootfs and hardware separately. The existing LG6851F donor image definition must never be renamed to SBAT6D or flashed.
