# Public source verification / 公開ソース検証

This repository is a **source-research snapshot**, not an installable OpenWrt firmware release.
All commands below run on a Linux development host; none address the device.

## Reproduce the upstream MediaTek Ethernet RFC object build

Verified GitHub Actions results (2026-10-23):

- [ARM64 baseline, RFC1, RFC1+RFC2 object compilation](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39877158871): PASS
- [Pinned upstream source and sequential patch application](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/39877158897): PASS

Host: Ubuntu 24.04 or comparable Debian/Ubuntu host with AArch64 cross tools. This reproduces an **object compilation**, not a complete kernel, rootfs, firmware or bootloader.

```sh
sudo apt-get update
sudo apt-get install -y git gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu make bc bison flex libssl-dev libelf-dev
git clone https://github.com/Karin-Laboratory/openwrt-terminal-6.git
cd openwrt-terminal-6
REPO="$(pwd)"
git clone --depth 1 --branch v6.18 --single-branch https://github.com/torvalds/linux.git linux
cd linux
test "$(git hash-object drivers/net/ethernet/mediatek/mtk_eth_soc.c)" = e68997a29191b2a8ce0868873dcfe95c79e10e56
test "$(git hash-object drivers/net/ethernet/mediatek/mtk_eth_soc.h)" = 0168e2fbc6197a6aa9fe159767166e86915accbc
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig
scripts/config --enable CONFIG_COMPILE_TEST --enable CONFIG_NET_VENDOR_MEDIATEK --enable CONFIG_NET_MEDIATEK_SOC --enable CONFIG_NET_DSA
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
grep -Eq '^CONFIG_NET_MEDIATEK_SOC=(y|m)$' .config
OBJ=drivers/net/ethernet/mediatek/mtk_eth_soc.o
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j2 "$OBJ"
sha256sum "$OBJ"
rm "$OBJ"
git apply --check "$REPO/patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch"
git apply "$REPO/patches/rfc/0001-mediatek-quiesce-workers-before-cleanup.patch"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j2 "$OBJ"
sha256sum "$OBJ"
rm "$OBJ"
git apply --check "$REPO/patches/rfc/0002-mediatek-serialize-reset-requeue.patch"
git apply "$REPO/patches/rfc/0002-mediatek-serialize-reset-requeue.patch"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j2 "$OBJ"
sha256sum "$OBJ"
git diff --check
```

For the precise pinned CI host, configuration and recorded object digests, consult [the RFC2 report](RFC-2-RESET-REQUEUE.ja.md). Object hashes may change with compiler or build environment. Verify compiler success and source integrity first; do not treat differing object hashes from different toolchains as proof of failure.

## Verification boundaries

| Capability | Public evidence | Status |
| --- | --- | --- |
| RFC1→RFC2 source application | Upstream v6.18, two pinned source blobs, GitHub Actions | PASS |
| ARM64 `mtk_eth_soc.o` object compilation | Baseline, RFC1 and RFC1+RFC2, same CI configuration | PASS |
| Entire upstream kernel / OpenWrt image | No clean public build demonstrated | NOT VERIFIED |
| Real device Ethernet and Wi-Fi | Developer-reported observations only | NOT INDEPENDENTLY VERIFIED |
| Hardware-safe remove, watchdog and lockdep/KASAN | No hardware or instrumented kernel evidence | NOT VERIFIED |
| Third-party flash and recovery | No generally validated installation procedure | NO-GO |
| 5G modem | No supported public port | NOT SUPPORTED |

The public patches are RFC research only. No firmware image, manufacturer signing secret, calibration material, partition write command, or installable release is published.

日本語：本書のコマンドで再現できるのは**公開Linuxソースへの差分適用とARM64のオブジェクトコンパイル**までです。SoftBank Air Terminal 6向け完成ファームや安全な書込み手順ではありません。
