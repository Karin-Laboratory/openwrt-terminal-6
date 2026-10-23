# OpenWrt integration workstream (source only)

This directory is a *pre-integration* track, not a board profile or firmware builder. The Linux v6.18 RFC patches may only be applied to the exact pinned upstream blobs. An arbitrary OpenWrt patchset or kernel version must **not** be silently treated as compatible. See `scripts/apply-public-rfc-series.sh` for the hash-checked source gate.

Milestones: obtain independently reviewed SBAT6D board DTS; identify exact OpenWrt kernel target/version; compare MediaTek Ethernet C/header blob IDs; rebase patches if needed; build modules and full kernel in public CI; verify rootfs and hardware separately. The existing LG6851F donor image definition must never be renamed to SBAT6D or flashed.

## Locate an OpenWrt prepared kernel tree

After a normal, **source-only** OpenWrt `target/linux/prepare` run, the unpacked kernel normally resides under `build_dir/target-*/linux-*/linux-*`. Confirm the selected kernel version before integration. The checker accepts the kernel tree, **not** the OpenWrt repository root:

```sh
python3 tools/check_openwrt_rfc_compat.py /path/to/openwrt/build_dir/target-.../linux-.../linux-...
```

Only if both Git blob IDs match the exact pinned upstream Linux v6.18 files should the RFC1→RFC2 sequence be tested. For other kernel versions, a separate rebase plus full driver compilation and source-review is required. No vendor image target, package definition, board DTS or firmware output is implied.
