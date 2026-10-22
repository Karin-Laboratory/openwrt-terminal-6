# Donor source acquisition and board build isolation

**State: pinned public donor checkout is supported. SBAT6D compilation is NOT implemented or validated.**

Public donor: https://github.com/13179415360/openwrt-mt6990-lg6851f
Pinned revision: `a40df9a5afb46716dea799acea69f17480df4d82`

To retrieve the exact reference tree without building or signing:

```sh
bash scripts/fetch-donor-source.sh donor-source
git -C donor-source rev-parse HEAD
```

The donor README's `make` instructions are **not safe as an SBAT6D build guide**. The donor `target/linux/mediatek/image/mt6990.mk` defines `Device/fiberhome_lg6851f` and packages `boot_b.img`, using LG6851F metadata and its Android boot generator. The donor README says ordinary make builds signed A/B images and upgrade packages. Those files do not target our board.

## Required isolation before compilation

1. Freeze full donor source and feed revisions (git commit alone does not pin feeds/downloads).
2. Add a separate `Device/softbank_air_terminal_6` target using independently reviewed SBAT6D DTS, network setup and boot layout. Never reuse LG6851F DTS or signed images.
3. Provide target-specific non-installable kernel/DTS/rootfs **build targets only**, with no post-build signer/packer and no auto-flash command.
4. Audit all patches and firmware source/redistribution rights. Distribute no unit EEPROM, vendor image, private signing key or unauthorized artifacts.
5. Generate a source-to-output manifest, then validate clean CI compile and independent toolchain reproducibility.
6. Keep factory/sysupgrade/installable image generation disabled until explicit legal and hardware recovery gates pass.

## Files examined at pinned donor revision

- `target/linux/mediatek/Makefile`: Mediatek subtarget and kernel version (6.18).
- `target/linux/mediatek/mt6990/target.mk`: aarch64 / cortex-a55; device-specific inherited rootfs tools.
- `target/linux/mediatek/image/mt6990.mk`: LG6851F-specific device definition, DTS and Android boot packaging.
- `target/linux/mediatek/files-6.18/drivers/phy/mediatek/phy-mtk-mt6990-sgmii.c`: PHY reference, SPDX GPL-2.0-only; see [SDK mapping](../LICENSES/SDK-LINE-MAP.md).

The checkout script intentionally does not run `make`, `feeds install`, create images or contact hardware. **It is a source acquisition step, not a full reproducible OpenWrt build.**
