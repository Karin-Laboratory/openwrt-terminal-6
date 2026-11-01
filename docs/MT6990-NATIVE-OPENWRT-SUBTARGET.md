# MT6990 native OpenWrt source-only target bootstrap (PR-A)

This work ports the **minimal noninstallable target registration** proven in
PRIVATE Alpha 3, without porting any donor kernel/driver, calibration, OEM
material, image/signature logic or device access.

## Reproducible source inputs

- OpenWrt pinned commit: `5799d2da76998be50432b0a3325b42713b4b619b`
- Target: `mediatek/mt6990`
- Stage script: `tools/build/stage_mt6990_subtarget.py`
- Staged templates: `tools/build/mt6990-target/{target.mk,mt6990.mk}`
- Kconfig: minimal `config-6.18` generated from the script, not the full
  Air Terminal 6 hardware configuration.
- Source provenance: original research templates adapted from the project's
  PRIVATE Alpha 3 buildroot bootstrap, in which upstream `make defconfig`
  passed. All new source catalog entries remain `rights_review=pending`.
  The upstream OpenWrt tree is fetched separately and is never committed.

## Local usage

Start from a **clean, isolated checkout** of the exact pinned OpenWrt commit,
then run:

```sh
python3 tools/build/stage_mt6990_subtarget.py \
  --tree /absolute/path/to/pinned-openwrt \
  --report /absolute/path/to/new-report.json
cat > /absolute/path/to/pinned-openwrt/.config <<'EOF'
CONFIG_TARGET_mediatek=y
CONFIG_TARGET_mediatek_mt6990=y
EOF
( cd /absolute/path/to/pinned-openwrt && umask 022 && make defconfig )
grep -qx 'CONFIG_TARGET_mediatek_mt6990=y' /absolute/path/to/pinned-openwrt/.config
```

The source is checked for exact upstream commit, clean git status, expected
MediaTek Makefile, safe templates, and absence of a Device profile. The script
writes four explicitly allowed upstream source files in the isolated tree:
MediaTek Makefile, subtarget target.mk, generated config-6.18, image mt6990.mk.
It writes a JSON report outside that tree, but **never** builds an Image,
p25/p26, or any installable firmware.

The dedicated GitHub-hosted PR workflow runs the synthetic tests and a real
upstream OpenWrt `make defconfig`; it neither touches hardware nor uses a
private/self-hosted runner or signing credentials.

## What passing the target gate means

A successful `make defconfig` proves only that a pinned OpenWrt source tree
accepts the additional MT6990 subtarget. It **does not** prove kernel
compilation, DTB correctness, NETSYS/PCS1/SGMII1 operation, PCIe/Wi-Fi,
OpenWrt package compilation, AP startup, p25/p26 layout, LK compatibility,
vendor license clearance or a safe hardware recovery path.

Do not claim a running Air Terminal 6 from a PASS here. Further work belongs
in [Issue #20](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/20),
[Issue #21](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/21),
[Issue #74](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/74),
with source publication and firmware release restrictions maintained in
[Issue #2](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/2).
