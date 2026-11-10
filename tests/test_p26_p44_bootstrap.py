# SPDX-License-Identifier: MIT
"""Independent source-only tests; never access physical P25/P26/P44."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
from tools.boot import build_p26_p44_initramfs as maker
from tools.boot import verify_p26_p44_initramfs as reader


class ExperimentalP26P44BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "staged-rootfs"
        for name in ("bin", "sbin", "etc"):
            (self.root / name).mkdir(parents=True)
        (self.root / "bin/busybox").write_bytes(b"synthetic target file")
        (self.root / "sbin/procd").write_bytes(b"synthetic target procd")
        (self.root / "sbin/init").symlink_to("procd")
        (self.root / "etc/preinit").write_text("#!/bin/sh\nexit 0\n")
        self.p26 = self.base / "p26.img"
        self.p26.write_bytes(b"x" * 4096)
        self.p26_receipt = self.base / "p26.json"
        self.p26_receipt.write_text(json.dumps({
            "partition_bytes": 4096,
            "p26_sha256": hashlib.sha256(self.p26.read_bytes()).hexdigest(),
        }))
        self.cpio = self.base / "alternate.cpio"
        self.receipt = self.base / "alternate.json"

    def build(self):
        with mock.patch.object(maker, "PARTITION_BYTES", 4096):
            return maker.package(self.root, self.p26, self.p26_receipt,
                                 self.cpio, self.receipt)

    def verify(self):
        with mock.patch.object(maker, "PARTITION_BYTES", 4096):
            return reader.verify(self.root, self.p26, self.p26_receipt,
                                 self.cpio, self.receipt)

    def test_actual_newc_from_staged_rootfs_is_verified_independently(self):
        record = self.build()
        self.assertGreater(record["cpio_bytes"], 128)
        result = self.verify()
        self.assertEqual(result["status"], "P26_P44_CPIO_INDEPENDENT_FULL_READBACK_PASS")
        self.assertFalse(result["device_boot_proven"])
        self.assertFalse(record["owner_rw_approval_embedded"])

    def test_tampered_cpio_fails_even_with_unchanged_p26(self):
        self.build()
        with self.cpio.open("r+b") as stream:
            stream.seek(180)
            stream.write(b"X")
        with self.assertRaisesRegex(ValueError, "BOOTSTAGE_CPIO_SHA_MISMATCH"):
            self.verify()

    def test_changed_p26_rejects_old_binding(self):
        self.p26.write_bytes(b"y" * 4096)
        with self.assertRaisesRegex(ValueError, "AIR6_STAGE_P26_INDEPENDENT_SHA"):
            self.build()

    def test_private_p44_consent_must_not_be_embedded(self):
        (self.root / "etc/air6-owner-p44-rw-go").write_text(
            "AIR6_P44_RW_OWNER_APPROVED_FOR_THIS_PAIR")
        with self.assertRaisesRegex(ValueError, "ROOTFS_PROTECTED"):
            self.build()
        self.assertFalse(self.cpio.exists())

    def test_symlinked_init_checks_real_procd_and_journal_replay(self):
        script = maker.BOOT_SCRIPT.read_text()
        self.assertIn('readlink "$ROM/sbin/init"', script)
        self.assertIn('readlink "$NEWROOT/sbin/init"', script)
        self.assertIn('cmp -s "$ROM/sbin/procd" "$NEWROOT/sbin/procd"', script)
        self.assertIn("P44_POST_JOURNAL_BOOT_SHADOW", script)
        self.assertIn('if [ -L "$ROM/sbin/init" ]; then', script)

    def test_default_ram_overlay_does_not_probe_p44(self):
        source = maker.BOOT_SCRIPT.read_text()
        self.assertIn('P26_RAM_OVERLAY_DEFAULT', source)
        self.assertIn('mount -t tmpfs -o mode=0700,size=64m,nosuid,nodev', source)
        self.assertIn('BACKING="$RAM"', source)
        self.assertIn('mount --move "$BACKING" "$NEWROOT/overlay"', source)
        owner_guard = source.index('if [ ! -e "$OWNER_GO" ] && [ ! -L "$OWNER_GO" ]; then')
        p44_mount = source.index('mount -t ext4 -o ro,noload "$P44" "$UPPER"')
        self.assertLess(owner_guard, p44_mount)
        self.assertLess(source.index('[ "$observed" = "$expected" ]'),
                        source.index('mount -t tmpfs -o mode=0700,size=64m,nosuid,nodev'))

    def test_invalid_owner_marker_still_fails_closed(self):
        source = maker.BOOT_SCRIPT.read_text()
        self.assertIn('halt_boot P44_RW_TOKEN_NOT_MATCHED', source)
        self.assertIn('halt_boot P44_GPT_PARTNAME', source)
        self.assertIn('halt_boot P44_POST_JOURNAL_BOOT_SHADOW', source)
        self.assertIn('log P44_OWNER_APPROVED', source)
        self.assertIn('if [ ! -e "$OWNER_GO" ] && [ ! -L "$OWNER_GO" ]; then', source)

    def test_target_busybox_parses_ram_init_in_isolated_qemu(self):
        workflow = (maker.ROOT / ".github/workflows/mt6990-native-subtarget.yml").read_text()
        self.assertIn("qemu-aarch64 -L /rootfs -0 sh /rootfs/bin/busybox -n /air6-init.sh",
                      workflow)
        self.assertIn("qemu-aarch64 -L /rootfs -0 sh /rootfs/bin/busybox /air6-init.sh --capabilities",
                      workflow)
        self.assertIn("PUBLIC_MT6990_NATIVE_TARGET_BUSYBOX_RAM_BOOT_SCRIPT_PARSE_PASS",
                      workflow)
        self.assertIn("--cap-drop ALL --security-opt no-new-privileges", workflow)

    def test_alternative_p26_aware_kernel_is_packed_into_separate_research_p25(self):
        workflow = (maker.ROOT / ".github/workflows/mt6990-native-subtarget.yml").read_text()
        self.assertIn("PUBLIC_MT6990_ALTERNATIVE_INITRAMFS_P25_P26_SAME_RUN_HASH_LINK_PASS", workflow)
        self.assertIn("gzip -dc \"$work/air6-p26-aware-Image.gz\" | cmp - \"$alternate_image\"", workflow)
        self.assertIn("PUBLIC_MT6990_ALTERNATIVE_IMAGE_GZIP_IDENTITY_PASS", workflow)
        self.assertIn("PUBLIC_MT6990_P26_AWARE_P25_INFLATED_IMAGE_IDENTITY_PASS", workflow)
        self.assertIn('size == kernel["inflated_bytes"]', workflow)
        self.assertIn('h.hexdigest() == kernel["inflated_sha256"]', workflow)
        self.assertLess(workflow.index("PUBLIC_MT6990_ALTERNATIVE_IMAGE_GZIP_IDENTITY_PASS"),
                        workflow.index("PUBLIC_MT6990_P26_AWARE_P25_INFLATED_IMAGE_IDENTITY_PASS"))

        self.assertIn("--output \"$work/p25-p26-aware-research-unsigned.img\"", workflow)
        self.assertIn("--kernel \"$work/air6-p26-aware-Image.gz\"", workflow)
        self.assertIn("--p25-receipt \"$work/p25-p26-aware-research.json\"", workflow)
        self.assertIn('pair["p26_sha256"] == cpio["p26_sha256"] == p26["p26_sha256"]', workflow)
        self.assertIn('pair["safe_to_flash"] is False', workflow)
        self.assertLess(workflow.index("PUBLIC_MT6990_NATIVE_ALTERNATIVE_RAM_INITRAMFS_IMAGE_BUILD_PASS"),
                        workflow.index("PUBLIC_MT6990_ALTERNATIVE_INITRAMFS_P25_P26_SAME_RUN_HASH_LINK_PASS"))
        self.assertIn('BLOCKED_SYNTHETIC_OR_UNREVIEWED_P25_METADATA', workflow)
        self.assertIn("PUBLIC_MT6990_P26_AWARE_P25_FDT_STRUCTURAL_CONTRACT_PASS", workflow)
        self.assertIn('result["status"] == "STRUCTURAL_ONLY_LK_UNVERIFIED"', workflow)
        self.assertIn('result["sign_ready"] is False', workflow)
        self.assertIn("--dtb-section \"$kernel/arch/arm64/boot/dts/mediatek/mt6990-air-terminal-6.dtb\"", workflow)
        self.assertLess(workflow.index("PUBLIC_MT6990_P26_AWARE_P25_FDT_STRUCTURAL_CONTRACT_PASS"),
                        workflow.index("PUBLIC_MT6990_ALTERNATIVE_INITRAMFS_P25_P26_SAME_RUN_HASH_LINK_PASS"))


    def test_native_toolchain_is_real_and_precedes_kernel_build(self):
        workflow = (maker.ROOT / ".github/workflows/mt6990-native-subtarget.yml").read_text()
        self.assertIn('make -C "$work/openwrt" -j1 V=s toolchain/install', workflow)
        self.assertIn('PUBLIC_MT6990_NATIVE_TOOLCHAIN_PRE_KERNEL_PASS', workflow)
        self.assertIn('BLOCKED_NATIVE_TOOLCHAIN_GCC_NOT_INSTALLED', workflow)
        self.assertIn('BLOCKED_NATIVE_TOOLCHAIN_LD_NOT_INSTALLED', workflow)
        self.assertIn('aarch64-openwrt-linux-musl-gcc', workflow)
        self.assertLess(workflow.index('make -C "$work/openwrt" -j1 V=s toolchain/install'),
                        workflow.index('PUBLIC_MT6990_NATIVE_TOOLCHAIN_PRE_KERNEL_PASS'))
        self.assertLess(workflow.index('PUBLIC_MT6990_NATIVE_TOOLCHAIN_PRE_KERNEL_PASS'),
                        workflow.index('make -C "$work/openwrt" -j2 V=s target/linux/compile'))
        # A shell line continuation after a comment can hide the make command.
        self.assertNotIn('toolchain/install\\\\n', workflow)

    def test_qemu_busybox_direct_target_applet_dispatch(self):
        # OpenWrt BusyBox can omit the 'busybox' dispatcher while retaining
        # sh/mount/etc. Probe actual target applets by argv[0], and do not
        # substitute a host binary or silently accept QEMU errors.
        workflow = (maker.ROOT / ".github/workflows/mt6990-native-subtarget.yml").read_text()
        self.assertIn('for applet in sh mount umount sha256sum switch_root grep cat readlink cmp mkdir sleep; do', workflow)
        self.assertIn('qemu-aarch64 -L /rootfs -0 "$applet" /rootfs/bin/busybox --help', workflow)
        self.assertIn('PUBLIC_MT6990_NATIVE_TARGET_BUSYBOX_DIRECT_APPLET_PROBES_PASS', workflow)
        self.assertIn('BLOCKED_TARGET_BUSYBOX_QEMU_APPLET_RUNTIME_$applet', workflow)
        self.assertIn("BLOCKED_TARGET_BUSYBOX_HELP_OUTPUT_NOT_VERIFIED_$applet", workflow)
        self.assertIn("grep -Fq 'BusyBox v'", workflow)
        self.assertIn('--target-busybox-applets "$work/target-openwrt-busybox-applets.txt"', workflow)
        self.assertIn('--network none --read-only', workflow)
        self.assertIn('--cap-drop ALL --security-opt no-new-privileges', workflow)
        self.assertNotIn('qemu-aarch64 -L /rootfs -0 /bin/busybox /rootfs/bin/busybox', workflow)

    def test_qemu_virt_alternative_init_actual_pid1_missing_p26_gate(self):
        # Native kernel must embed the alternate verified CPIO AFTER the
        # known-good research p25/QEMU stages, without changing their receipts.
        wf = (maker.ROOT / ".github/workflows/mt6990-native-subtarget.yml").read_text()
        self.assertIn('--set-str INITRAMFS_SOURCE "$work/air6-p26-p44-alternative.cpio"', wf)
        self.assertIn('AIR6_RAM_INIT_ENTER', wf)
        self.assertIn('AIR6_BOOT_BLOCKED_P26_NOT_BLOCK', wf)
        self.assertIn('PUBLIC_MT6990_QEMU_VIRT_ALTERNATIVE_INIT_MISSING_P26_FAILCLOSED_PASS', wf)
        self.assertIn('dst=/AlternativeImage,readonly', wf)
        self.assertLess(wf.index('PUBLIC_MT6990_NATIVE_EPHEMERAL_P25_P26_SAME_RUN_PAIR'),
                        wf.index('PUBLIC_MT6990_NATIVE_ALTERNATIVE_RAM_INITRAMFS_IMAGE_BUILD_PASS'))
        self.assertIn('test "$(sha256sum "$alternate_image" | cut -d\' \' -f1)" != "$known_image_sha"', wf)
        self.assertIn('-nic none -no-reboot', wf)
        self.assertIn('--network none --read-only', wf)

    def test_shell_syntax_and_non_operational_capabilities_only(self):
        script = maker.BOOT_SCRIPT
        check = subprocess.run(["sh", "-n", str(script)], capture_output=True)
        self.assertEqual(check.returncode, 0, check.stderr.decode())
        res = subprocess.run(["sh", str(script), "--capabilities"],
                             capture_output=True, text=True, timeout=5)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("NO_AUTO_RECOVERY", res.stdout)
        self.assertIn("P44_EXPLICIT_RW_GO", res.stdout)
        body = script.read_text()
        self.assertNotIn("mkfs", "\n".join(
            line for line in body.splitlines() if not line.lstrip().startswith("#")))
        self.assertNotIn("bootctrl", "\n".join(
            line for line in body.splitlines() if not line.lstrip().startswith("#")))
        self.assertNotIn("reboot", "\n".join(
            line for line in body.splitlines() if not line.lstrip().startswith("#")))


if __name__ == "__main__":
    unittest.main()
