#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Actual same-workspace source build: Debian PR14 public 6.18.63 network kernel,
# OpenWrt's already manufactured P26-bound first stage, existing public P25
# producer and independent P25/P26 verifier. No private binary or signing.
set -euo pipefail
[[ $# == 5 ]] || { echo 'usage: script FRESH_ABS_DIR CPIO P26 PRODUCER INDEPENDENT' >&2; exit 2; }
out="$1"; cpio="$2"; p26="$3"; producer="$4"; independent="$5"
root="$(cd "$(dirname "$0")/.." && pwd -P)"
for p in "$out" "$cpio" "$p26" "$producer" "$independent"; do
  [[ $p == /* ]] || { echo 'PUBLIC_PAIR_BLOCKED_ABSOLUTE_PATH_REQUIRED' >&2; exit 2; }
done
[[ $out != / && ! -e $out && ! -L $out && -d $(dirname "$out") ]] ||
  { echo 'PUBLIC_PAIR_BLOCKED_OUTPUT_NOT_FRESH' >&2; exit 2; }
for p in "$cpio" "$p26" "$producer" "$independent"; do
  [[ -f $p && ! -L $p ]] || { echo 'PUBLIC_PAIR_BLOCKED_MISSING_INPUT' >&2; exit 2; }
done
[[ $(stat -c %s "$p26") == 134217728 ]] ||
  { echo 'PUBLIC_PAIR_BLOCKED_REAL_P26_SIZE' >&2; exit 1; }
for bin in git python3 make dtc cpp sha256sum gzip; do
  command -v "$bin" >/dev/null || { echo "PUBLIC_PAIR_BLOCKED_TOOL_$bin" >&2; exit 2; }
done
[[ -n ${AIR6_CROSS_COMPILE:-} ]] || { echo "PUBLIC_PAIR_BLOCKED_MATCHING_OPENWRT_CROSS_PREFIX_REQUIRED" >&2; exit 2; }
command -v "${AIR6_CROSS_COMPILE}gcc" >/dev/null || { echo "PUBLIC_PAIR_BLOCKED_CROSS_COMPILER" >&2; exit 2; }
command -v "${AIR6_CROSS_COMPILE}ld" >/dev/null || { echo "PUBLIC_PAIR_BLOCKED_CROSS_LINKER" >&2; exit 2; }
# A compiler prefix may exist yet target the wrong architecture. Reject it
# before the expensive pinned-source checkout and kernel build.
compiler_target="$("${AIR6_CROSS_COMPILE}gcc" -dumpmachine)" ||
  { echo 'PUBLIC_PAIR_BLOCKED_CROSS_COMPILER_TARGET_QUERY' >&2; exit 2; }
# -dumpmachine must be exactly one plausible target triplet, not a prefix
# followed by whitespace, a second line, or arbitrary injected text.
if [[ ! "$compiler_target" =~ ^aarch64-[a-zA-Z0-9_.+-]+$ ]]; then
  echo "PUBLIC_PAIR_BLOCKED_CROSS_COMPILER_TARGET:$compiler_target" >&2
  exit 2
fi
linker_target="$("${AIR6_CROSS_COMPILE}ld" -V 2>&1)" ||
  { echo 'PUBLIC_PAIR_BLOCKED_CROSS_LINKER_TARGET_QUERY' >&2; exit 2; }
# Reject lookalike tool output even when it fabricates an emulation section.
# The toolchain contract is GNU binutils ld, not an arbitrary -V responder.
if [[ ! "$linker_target" =~ ^GNU[[:space:]]ld([[:space:]]|$) ]]; then
  echo "PUBLIC_PAIR_BLOCKED_CROSS_LINKER_IDENTITY" >&2
  exit 2
fi
# aarch64 entry does not prove that the default linker output is ARM64.
linker_default="$(printf '%s\n' "$linker_target" | awk '/^[[:space:]]*Supported emulations:[[:space:]]*$/ { if (getline > 0 && NF == 1) print $1; exit }')"
case "$linker_default" in
  aarch64linux|aarch64elf) ;;
  *) echo "PUBLIC_PAIR_BLOCKED_CROSS_LINKER_TARGET:$linker_default" >&2; exit 2 ;;
esac
mkdir -m 0700 "$out"
# Pin the PUBLIC Debian PR14 source, then let its independent 17-blob source
# manifest verify every MT6990 donor input. No private source import.
pin=e05811f8d4d3ee2606f44f27218ef59132a39a5f
git clone -q --filter=blob:none --no-checkout \
  https://github.com/Karin-Laboratory/Debian13-Terminal6.git "$out/debian-public"
git -C "$out/debian-public" fetch -q --depth=1 origin "$pin"
git -C "$out/debian-public" checkout -q --detach "$pin"
[[ $(git -C "$out/debian-public" rev-parse HEAD) == "$pin" ]] ||
  { echo 'PUBLIC_PAIR_BLOCKED_DEBIAN_REVISION' >&2; exit 1; }
deb="$out/debian-public"
bash "$deb/scripts/stage-experimental-dtb.sh" "$out/dtb"
python3 "$deb/scripts/stage-public-mt6990-sources.py" --output "$out/public-mt6990"
# Use a LOCAL modified copy of the MIT-licensed pinned Debian build recipe.
# Only add the P26-bound OpenWrt initramfs+XZ built-in requirements.
python3 - "$deb/scripts/build-linux-6.18.sh" "$deb/scripts/build-openwrt-pair-local.sh" <<'PY'
from pathlib import Path
import hashlib, sys
raw = Path(sys.argv[1]).read_bytes()
blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
if blob != "d84143d75d185c5f90b0296b92bf0fb2fcbb2867":
    raise SystemExit("PUBLIC_PAIR_BLOCKED_DEBIAN_SCRIPT_BLOB_CHANGED")
src = raw.decode("utf-8")
needle = 'if [[ -n "' + chr(36) + '{INITRAMFS_ARCHIVE:-}" ]]; then\n'
if src.count(needle) != 1:
    raise SystemExit("PUBLIC_PAIR_BLOCKED_KERNEL_SCRIPT_ANCHOR")
addition = ('scripts/config --enable SQUASHFS --enable SQUASHFS_XZ '
            '--enable OVERLAY_FS --enable CRYPTO_SHA256 '
            '--enable RD_XZ --enable INITRAMFS_COMPRESSION_XZ '
            '--disable INITRAMFS_COMPRESSION_GZIP\n')
Path(sys.argv[2]).write_text(src.replace(needle, addition + needle))
PY
export PUBLIC_MT6990_STAGE="$out/public-mt6990"
export PUBLIC_MT6990_SCOPE=network
export WORKDIR="$out/linux-6.18.63"
export INITRAMFS_ARCHIVE="$cpio"
export DTB_PATH="$out/dtb/board/terminal6-debian-ethernet-experimental.dtb"
export CROSS_COMPILE="$AIR6_CROSS_COMPILE"
export JOBS=4
bash "$deb/scripts/build-openwrt-pair-local.sh"
kernel="$out/linux-6.18.63"
image="$kernel/arch/arm64/boot/Image"
dtb="$DTB_PATH"
[[ -s $image && -s $kernel/vmlinux && -s $kernel/usr/initramfs_data.o ]] ||
  { echo 'PUBLIC_PAIR_BLOCKED_REAL_KERNEL_IMAGE' >&2; exit 1; }
for option in CONFIG_ARCH_MEDIATEK=y CONFIG_MMC_MTK=y CONFIG_NET_MEDIATEK_SOC=y \
  CONFIG_PCS_MTK_LYNXI=y CONFIG_NET_DSA_MT7530=y \
  CONFIG_SQUASHFS=y CONFIG_SQUASHFS_XZ=y CONFIG_INITRAMFS_COMPRESSION_XZ=y; do
  grep -qx "$option" "$kernel/.config" ||
    { echo "PUBLIC_PAIR_BLOCKED_KERNEL_CONFIG_$option" >&2; exit 1; }
done
gzip -n -9 -c "$image" > "$out/air6-public-Image.gz"
python3 "$root/tools/boot/verify_kernel_initramfs.py" \
  --object "$kernel/usr/initramfs_data.o" --vmlinux "$kernel/vmlinux" \
  --image "$image" --kernel-gz "$out/air6-public-Image.gz" \
  --cpio "$cpio" --compression xz
: > "$out/empty-boot-ramdisk"
python3 "$root/tools/boot/make_p25_dtb_table.py" \
  --dtb "$dtb" --page-size 2048 --output "$out/aosp-dt-table64.bin"
# Convert Debian's PUBLIC numeric boot-v2 profile into OpenWrt's existing
# boot-v2 schema, with a newly sized AOSP header (never copied OEM bytes).
python3 - "$deb/configs/public-air6-boot-v2-profile.json" \
  "$out/aosp-dt-table64.bin" "$out/openwrt-boot-v2-profile.json" <<'PY'
import hashlib,json,pathlib,sys
src=json.loads(pathlib.Path(sys.argv[1]).read_text())
required={'cmdline','dtb_addr','header_size','header_version','kernel_addr',
          'name','os_version','page_size','ramdisk_addr','second_addr','tags_addr'}
assert set(src)==required and (src['page_size'],src['header_version'],
        src['header_size'],src['name'])==(2048,2,1660,"mt6990")
prefix=pathlib.Path(sys.argv[2]).read_bytes()
assert len(prefix)==64
profile={k:"0x%x"%src[k] for k in
         ('kernel_addr','ramdisk_addr','second_addr','tags_addr','dtb_addr')}
profile.update({"page_size":2048,"os_version":src['os_version'],
    "name":"mt6990","cmdline":"bootopt=64S3,32N2,64N2 init_debug=4 console=ttyS0,115200n8 earlycon",
    "ramdisk_mode":"kernel_embedded","dtb_prefix_bytes":64,
    "dtb_prefix_sha256":hashlib.sha256(prefix).hexdigest()})
pathlib.Path(sys.argv[3]).write_text(json.dumps(profile,sort_keys=True,indent=2)+"\n")
PY
mkdir -m 0700 "$out/unsigned-pair"
p25="$out/unsigned-pair/boot_a.unsigned.p25"
profile="$out/openwrt-boot-v2-profile.json"
prefix="$out/aosp-dt-table64.bin"
kernel_gz="$out/air6-public-Image.gz"
empty="$out/empty-boot-ramdisk"
python3 "$root/tools/boot/pack_p25_unsigned_v2.py" \
  --kernel "$kernel_gz" --ramdisk "$empty" --dtb "$dtb" \
  --dtb-prefix "$prefix" --config "$profile" --output "$p25"
python3 "$root/tools/boot/verify_p25_independent.py" \
  --p25 "$p25" --kernel "$kernel_gz" --ramdisk "$empty" \
  --dtb "$dtb" --dtb-prefix "$prefix" --config "$profile"
python3 "$root/tools/build/verify_unsigned_pair.py" \
  --p25 "$p25" --kernel "$kernel_gz" --ramdisk "$empty" \
  --dtb "$dtb" --dtb-prefix "$prefix" --config "$profile" \
  --p26 "$p26" --producer "$producer" --independent "$independent" \
  --cpio "$cpio" --initramfs-object "$kernel/usr/initramfs_data.o" \
  --vmlinux "$kernel/vmlinux" --image "$image" \
  --out "$out/unsigned-pair/same-run-p25-p26-receipt.json"
[[ $(stat -c %s "$p25") == 33554432 ]] ||
  { echo 'PUBLIC_PAIR_BLOCKED_P25_SIZE' >&2; exit 1; }
[[ $(stat -c %s "$p26") == 134217728 ]] ||
  { echo 'PUBLIC_PAIR_BLOCKED_P26_SIZE' >&2; exit 1; }
# Read the complete images again from the ephemeral runner filesystem.
echo 'PUBLIC_OPENWRT_61863_UNSIGNED_P25_P26_SOURCE_PAIRCHECK_PASS'
sha256sum "$p25" "$p26"
echo 'AIR6_LK_BOOT_LAN_SSH_P44_WIFI_PHY_NOT_TESTED'
echo 'NO_BINARY_ARTIFACT_UPLOAD_NO_DEVICE_WRITE_NO_SIGNING'
