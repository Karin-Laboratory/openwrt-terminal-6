# Unsigned p26 rootfs_a packing lane (draft, 2026-11-04)

**Status (2026-11-10):** a public-source-built 128 MiB p26 with independent SquashFS/readback verification was recorded on the PR #127 base at commit `aabe6ac11e13093c6929ff1676ecd54bed2aae1b` (Actions run [#42350310859](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/42350310859), SHA-256 `c55884a21dddac40569689b90c3911d3400092d652278b9deb8a009145b23c35`). That image predates the PR #133 P44 extension changes and is **not** the current PR #133 output.

At the start of the 2026-11-10 follow-up, PR #133 head `c6c33643e45d328bfa263323a37854d37f87358f` had an exact-head P26 production/readback job queued as Actions run [#42794634887](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/42794634887). This follow-up changes the build workflow's reporting, so that older run cannot validate the new workflow blob. The P44-extended P26 remains unverified until the latest PR #133 head passes its own job; its SHA must not be replaced with the PR #127 hash.
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


## PR #118 to PR #127 handoff (not yet executed)

PR #118 is an **unmerged Draft** and its workflow is a separate branch. A passing native package-build job on PR #127 does **not** prove that the PR #118 `wpad-basic-mbedtls` changes were in that job's checkout. Before claiming AP userspace readiness, verify the exact workflow blob and the checkout commit from the same run; do not combine success statuses from unrelated PR heads.

For an owner-controlled offline replay, use this fail-closed sequence:

1. Record the exact source checkout SHA, OpenWrt pin, workflow SHA, `make defconfig` output, installed package manifest and successful `package/install` log from **one** run. Check whether `wpad-basic-mbedtls` is actually selected and present, rather than inferring it from the PR title.
2. Extract the staged `rootfs-stage.tar.gz` into a new, private directory without following archive symlinks outside that directory; inspect its members and numeric ownership first. Do not reuse a synthetic CI fixture as the input. The archive is an intermediate rootfs, not a p26 image.
3. Verify the extracted tree contains the executables named in the packer contract, has a locked root account, has no unprovisioned SSH/radio autostart, and contains neither credentials nor firmware/calibration. For an AP-enabled candidate, additionally check `/usr/sbin/wpad` and the `hostapd` symlink; those are **not** required to establish the LAN-only p26 milestone.
4. Construct the JSON source receipt from the **observed** run and installed package manifest. Do not copy the illustrative receipt above with `source_built: true` without independent evidence. Keep the receipt and output directory private.
5. Run the unsigned packer, then perform a separate full-tree `unsquashfs` comparison and independent 128 MiB readback, including zero-padding and full SHA. Keep `P26_BUILD=BLOCKED` until the ownership/xattr and provenance gates below are satisfied.

No signing, device flashing, boot-slot changes, reboot, or artifact publication is part of this handoff. This section is a procedure, **not** a record that the steps have run.

## Remaining hard acceptance requirements

1. Rebuild from the pinned public OpenWrt source and inspect actual package versions/dependency closure, package licenses, feed use, and first-boot service policy. The existing hosted CI is a credible source of *package* evidence, but its `rootfs-stage.tar.gz` is not a p26.
2. Preserve/verify **numeric UID/GID, modes, all symlinks, xattrs/capabilities where needed**. This first packer does not reconstruct the private R34 pseudo-file owner map and uses `-no-xattrs`; it must not be claimed equivalent to the R34 production contract until those requirements are resolved.
3. Run `unsquashfs` in a separate process on the newly built image; compare the complete file tree and link/ownership/mode inventory, then read back the full 128 MiB bytes and zero padding. Verify reproducibility with a pinned `squashfs-tools` revision and an independent rebuild.
4. Confirm minimal LAN configuration, wired driver/DTB availability and key-only SSH provisioning as separate acceptance gates. **No credentials, private key, EEPROM, modem calibration or radio firmware** may enter public inputs. Wi-Fi and modem remain optional rights-gated modules. NR/IPv6/6GHz/EasyMesh are not prerequisites.

For a given commit, report `P26_BUILD=BLOCKED` unless that exact commit has a successful source-built P26 and independent filesystem/readback attestation. The older PR #127 result demonstrates the packer path, not the newer P44-extended tree. Separately, P25 remains blocked until an independently validated boot-v2 config and a boot-capable C-unit DTB/kernel input set are available; a successful byte-layout/pair check would still not establish LK acceptance or a physical boot.
