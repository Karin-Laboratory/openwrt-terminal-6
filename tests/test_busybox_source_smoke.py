# SPDX-License-Identifier: MIT
"""Static security contract for a source-only, non-installable ARM64 userland smoke."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build-arm64-busybox-smoke.sh"


class BusyBoxSourceSmokeTests(unittest.TestCase):
    def test_upstream_commit_and_makefile_are_pinned(self):
        src = SCRIPT.read_text()
        self.assertIn("mirror/busybox.git", src)
        self.assertIn("1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4", src)
        self.assertIn("fa8cb761443388730372eaf260e7ca1a0235bc43", src)
        self.assertIn("ARCH=arm64 CROSS_COMPILE", src)
        self.assertIn("CONFIG_TC is not set", src)
        self.assertIn("older Linux UAPI types", src)

    def test_no_install_flash_sign_keys_or_execution(self):
        src = SCRIPT.read_text()
        for forbidden in (
            "sudo ", "apt install", "sysupgrade", "fastboot",
            "dd if=", "scp ", "ssh root@", "flashrom",
            "sign-image", "gpg --import", "make install",
            "qemu-aarch64", "chroot ", "socat ", "curl | sh",
        ):
            self.assertNotIn(forbidden, src)
        self.assertIn('EUID == 0', src)
        self.assertIn('trap \'rm -rf -- "$tmp"\' EXIT', src)

    def test_header_check_requires_aarch64(self):
        src = SCRIPT.read_text()
        self.assertIn("header[:4]", src)
        self.assertIn("header[4] != 2", src)
        self.assertIn("header[5] != 1", src)
        self.assertIn("!= 183", src)
        self.assertIn("never execute", src)

    def test_single_build_and_elf_header_check(self):
        src = SCRIPT.read_text()
        self.assertEqual(src.count("timeout 450s make"), 1)
        self.assertEqual(src.count("<<'PY'"), 1)
        self.assertEqual(src.count("BUSYBOX_ARM64_ELF_HEADER_PASS"), 1)
        self.assertNotIn("CONFIG_TC=ytimeout", src)

    def test_native_musl_mode_uses_explicit_compiler_and_pinned_libc(self):
        src = SCRIPT.read_text()
        self.assertIn("native-musl-static-stage", src)
        self.assertIn("native-musl-static-initramfs", src)
        self.assertIn("SBAT6_MUSL_CC", src)
        self.assertIn('cc_override=("CC=$compiler")', src)
        self.assertIn("musl-static", src)
        musl = (ROOT / "scripts/build-arm64-musl-busybox-stage.sh").read_text()
        self.assertIn("ifduyue/musl.git", musl)
        self.assertIn("0784374d561435f7c787a555aeab8ede699ed298", musl)
        self.assertIn("native-musl-static-stage", musl)
        self.assertIn("native-musl-static-initramfs", musl)
        self.assertIn("SBAT6_NATIVE_MUSL_STATIC_PID1_INITRAMFS_PASS", musl)
        self.assertIn("7d0a66e4bb9081d75c82ec4957c50034cb0ea449", musl)
        self.assertIn("headers_install", musl)
        self.assertIn('INSTALL_HDR_PATH="$tmp/kernel-headers"', musl)
        self.assertIn("SBAT6_NATIVE_MUSL_STATIC_BUSYBOX_STAGE_PASS", musl)
        self.assertIn("EUID == 0", musl)
        self.assertNotIn("sudo ", musl)
        self.assertNotIn("make install DESTDIR=/", musl)
        self.assertIn("SBAT6_BUILD_LIBUBOX_CORE", musl)
        self.assertIn("build-arm64-musl-libubox-core.sh", musl)

    def test_pinned_musl_libubox_core_build_is_real_and_noninstallable(self):
        src = (ROOT / "scripts/build-arm64-musl-libubox-core.sh").read_text()
        self.assertIn("openwrt/libubox.git", src)
        self.assertIn("da2d205a5cf3e877c45a2eec488218cbaf452e7d", src)
        self.assertIn("uloop.c", src)
        self.assertIn("udebug-remote.c", src)
        self.assertIn("libubox.a", src)
        self.assertIn("link-smoke.c", src)
        self.assertIn("SBAT6_MUSL_LIBUBOX_CORE_OBJECTS_AND_STATIC_LINK_PASS", src)
        self.assertIn("EUID == 0", src)
        for forbidden in ("sudo ", "apt install", "sysupgrade", "flashrom", "chroot ", "qemu-aarch64"):
            self.assertNotIn(forbidden, src)
        workflow = (ROOT / ".github/workflows/source-only-ci.yml").read_text()
        self.assertIn("SBAT6_BUILD_LIBUBOX_CORE=1", workflow)
        self.assertIn("SBAT6_BUILD_UBUS_CORE=1", workflow)
        self.assertIn("openwrt/ubus.git", src)
        self.assertIn("db20eff5535fe3126c05dc0edc029caf0e82fe10", src)
        self.assertIn("libubus-acl.c", src)
        self.assertIn("libubus.a", src)
        self.assertIn("ubus-link-smoke.c", src)
        self.assertIn("SBAT6_MUSL_LIBUBUS_CORE_OBJECTS_AND_STATIC_LINK_PASS", src)
        self.assertIn('if [[ "${SBAT6_BUILD_UBUS_CORE:-0}" == 1 ]]', src)

    def test_pinned_jsonc_and_ubusd_real_musl_static_link(self):
        src = (ROOT / "scripts/build-arm64-musl-libubox-core.sh").read_text()
        workflow = (ROOT / ".github/workflows/source-only-ci.yml").read_text()
        for needle in (
            "SBAT6_BUILD_UBUSD", "json-c/json-c.git",
            "41a55cfcedb54d9c1874f2f0eb07b504091d7e37",
            "libjson-c.a", "blobmsg_json.c", "libblobmsg_json.a",
            "ubusd_proto.c", "ubusd_acl.c", "ubusd_main.c",
            "libubusd.a", "SBAT6_MUSL_UBUSD_STATIC_DAEMON_LINK_PASS",
            "readelf -h", "readelf -l", "-static",
        ):
            self.assertIn(needle, src)
        self.assertIn("SBAT6_BUILD_UBUSD=1", workflow)
        self.assertIn('test "$(git -C "$json_src" rev-parse HEAD)" = "$json_revision"', src)
        self.assertIn("BUILD_SHARED_LIBS=OFF", src)
        self.assertIn("BUILD_TESTING=OFF", src)
        self.assertIn("EUID == 0", src)
        for forbidden in ("sudo ", "apt install", "sysupgrade", "flashrom",
                          "qemu-aarch64", "chroot ", "ssh root@"):
            self.assertNotIn(forbidden, src)

    def test_procd_service_compiles_upstream_sources_and_stages_real_elf(self):
        procd = (ROOT / "scripts/build-arm64-musl-procd-init.sh").read_text()
        stage = (ROOT / "scripts/build-arm64-musl-busybox-stage.sh").read_text()
        ci = (ROOT / ".github/workflows/source-only-ci.yml").read_text()
        for token in ("5aef7c33b01455157c1373a14e2a3fa47d024c6c",
                      "procd.c", "service/instance.c", "service/trigger.c",
                      "plug/hotplug.c", "json_script.c", "udebug.c",
                      "libubus_archive", "libuci_archive",
                      "SBAT6_MUSL_PROCD_SERVICE_STATIC_LINK_PASS",
                      "readelf -h", "readelf -l", "-static"):
            self.assertIn(token, procd)
        self.assertIn('SBAT6_BUILD_PROCD_SERVICE=1', ci)
        self.assertIn('SBAT6_MUSL_PROCD_SERVICE_OUTPUT', stage)
        self.assertIn('add("sbin/procd", tarfile.REGTYPE, 0o755, procd_service)', stage)
        self.assertIn('"sbin/procd": hashlib.sha256(procd_service).hexdigest()', stage)
        self.assertIn("SBAT6_MUSL_PROCD_SERVICE_ROOTFS_STAGE_PASS", stage)
        for forbidden in ("sudo ", "apt install", "sysupgrade", "flashrom",
                          "qemu-aarch64", "chroot ", "ssh root@", "dd if="):
            self.assertNotIn(forbidden, procd)

    def test_does_not_claim_rootfs_completeness(self):
        src = SCRIPT.read_text()
        self.assertIn("not an OpenWrt rootfs or board firmware", src)


if __name__ == "__main__":
    unittest.main()
