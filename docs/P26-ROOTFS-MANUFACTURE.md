# Unsigned p26 rootfs_a packing lane (draft, 2026-11-04)

**Status: PACKER SOURCE ONLY. No public-source-built 128 MiB p26 has yet been manufactured or independently verified.**
The authoritative policy is [MAINLINE-P25-P26-POLICY](MAINLINE-P25-P26-POLICY.md). No firmware distribution or device access is authorized.

## Reused, independently observed format

The owner-private Alpha 3 R34 manufacturing receipt (private PR #95) confirms a real XZ-compressed SquashFS followed by **zero padding to 134,217,728 bytes**. That receipt comes from a previously retained 221-APK image and **is not a public-source reproduction**. The private R34 producer/readback source established the format, numeric file ownership and byte-by-byte readback. This public lane does not import its image, secrets, vendor blobs or calibration.

## Existing public inputs

- Upstream OpenWrt checkout: pinned at `5799d2da76998be50432b0a3325b42713b4b619b` by `tools/build/stage_mt6990_subtarget.py`. The older userspace inspection plan's `5700101d...` commit is **not** this actual native build input.
- Installed OpenWrt root directory: `make package/install` in the existing `.github/workflows/mt6990-native-subtarget.yml`, which builds BusyBox, procd, ubus, uci, netifd and Dropbear. Draft PR #118 adds `wpad-basic-mbedtls` and must not be silently considered merged.
- `config/feeds.lock` fixes five feed revisions, but the current package build is drawn from the pinned core OpenWrt tree; do not claim these feeds were installed without an actual checkout/install receipt.
- Existing public QEMU guest validates procd, ubusd, netifd and an isolated bridge, not Air6 Ethernet, SSH login or device boot.

## Usage (private offline directory only)

This tool **does not build packages** and intentionally refuses a missing source receipt. Supply a directory produced by the exact public pinned OpenWrt `package/install` job, after locking the root account and removing unprovisioned SSH/radio autostart just as the existing CI does. Then provide a separate JSON receipt containing:

```json
{
  "openwrt_commit": "5799d2da76998be50432b0a3325b42713b4b619b",
  "source_built": true,
  "package_install": true,
  "packages": ["base-files", "busybox", "procd", "ubus", "uci", "netifd", "dropbear"],
  "feeds": {}
}
```

This is a **schema illustration, not evidence**. Do not mark `source_built` true unless independent build records prove it. Record actual package versions, upstream package revisions, enabled feed snapshots, SquashFS tools version, and ownership before any reproducibility claim. An empty feeds object means no additional feeds were installed; it is not proof of the five lock revisions.

```sh
python3 -m unittest discover -s tests -p 'test_pack_p26_rootfs.py' -v
python3 tools/build/pack_p26_rootfs.py \
  --rootfs /private/source-built/openwrt-root-mediatek \
  --source-receipt /private/source-built/provenance.json \
  --output /private/secure-new-output-directory
```

The output is `rootfs.squashfs`, `rootfs_a.p26`, and `p26-receipt.json`, all confined to the caller's private output directory. Never commit, cache, upload as an Actions artifact, or publish them. The receipt records a preliminary full-file SHA and partition size but explicitly states **AWAIT_INDEPENDENT_FS_READBACK**.

## Remaining hard acceptance requirements

1. Rebuild from the pinned public OpenWrt source and inspect actual package versions/dependency closure, package licenses, feed use, and first-boot service policy. The existing hosted CI is a credible source of *package* evidence, but its `rootfs-stage.tar.gz` is not a p26.
2. Preserve/verify **numeric UID/GID, modes, all symlinks, xattrs/capabilities where needed**. This first packer does not reconstruct the private R34 pseudo-file owner map and uses `-no-xattrs`; it must not be claimed equivalent to the R34 production contract until those requirements are resolved.
3. Run `unsquashfs` in a separate process on the newly built image; compare the complete file tree and link/ownership/mode inventory, then read back the full 128 MiB bytes and zero padding. Verify reproducibility with a pinned `squashfs-tools` revision and an independent rebuild.
4. Confirm minimal LAN configuration, wired driver/DTB availability and key-only SSH provisioning as separate acceptance gates. **No credentials, private key, EEPROM, modem calibration or radio firmware** may enter public inputs. Wi-Fi and modem remain optional rights-gated modules. NR/IPv6/6GHz/EasyMesh are not prerequisites.

Until these are demonstrated on an actual public-source-produced image, report `P26_BUILD=BLOCKED`, even if the host tests pass.
