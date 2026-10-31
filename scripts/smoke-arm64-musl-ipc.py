#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute pinned AArch64 musl ubusd/ubus/UCI in a rootless, local-only smoke.

Only selected ELF files are copied from the verified noninstallable rootfs
archive into a disposable private directory. No procd/PID1, netifd, network
interface, device node, flash, radio or privileged operation is exercised.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tarfile
import tempfile
import time

SCOPE = "NONINSTALLABLE_SBAT6_MUSL_BUSYBOX_UBUSD_UBUS_UCI_PROCD_NETIFD_ROOTFS_STAGE"
BINARIES = ("sbin/ubusd", "bin/ubus", "sbin/uci")
CONFIG = "etc/config/network"


def checked_payloads(archive_path: Path, manifest_path: Path) -> dict:
    if any(p.is_symlink() or not p.is_file() for p in (archive_path, manifest_path)):
        raise ValueError("rootfs and manifest must be regular files")
    raw = archive_path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("scope") != SCOPE or
            manifest.get("architecture") != "aarch64" or
            manifest.get("libc") != "native-musl-static-1.2.5" or
            manifest.get("rights_review") != "pending" or
            manifest.get("archive_sha256") != hashlib.sha256(raw).hexdigest() or
            manifest.get("archive_bytes") != len(raw)):
        raise ValueError("rootfs stage identity mismatch")
    result = {}
    with tarfile.open(archive_path, mode="r:gz") as archive:
        names = archive.getnames()
        if len(names) != len(set(names)):
            raise ValueError("duplicate archive members")
        for name in (*BINARIES, CONFIG):
            member = archive.getmember(name)
            if not member.isfile() or member.size > 8 * 1024 * 1024:
                raise ValueError("unexpected archive member: " + name)
            data = archive.extractfile(member).read()
            if manifest.get("files_sha256", {}).get(name) != hashlib.sha256(data).hexdigest():
                raise ValueError("archive payload mismatch: " + name)
            result[name] = data
    return result


def command(argv: list[str], *, timeout: int = 5) -> str:
    run = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                         text=True, timeout=timeout, check=False)
    if run.returncode:
        raise RuntimeError(f"{Path(argv[0]).name} returned {run.returncode}: "
                           + run.stderr[-1000:])
    return run.stdout


def smoke(archive: Path, manifest: Path) -> None:
    if os.geteuid() == 0 or platform.machine() != "aarch64":
        raise RuntimeError("only a non-root native AArch64 runner is allowed")
    payloads = checked_payloads(archive, manifest)
    with tempfile.TemporaryDirectory(prefix="sbat6-local-ipc-") as directory:
        root = Path(directory)
        for name in BINARIES:
            binary = root / Path(name).name
            binary.write_bytes(payloads[name])
            binary.chmod(0o700)
        config = root / "config"
        config.mkdir(mode=0o700)
        (config / "network").write_bytes(payloads[CONFIG])
        endpoint = str(root / "ubus.sock")
        if len(endpoint.encode()) > 100:
            raise RuntimeError("UNIX socket path too long")
        daemon = subprocess.Popen(
            [str(root / "ubusd"), "-s", endpoint],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, cwd=root,
        )
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if daemon.poll() is not None:
                    raise RuntimeError(f"ubusd exited early: {daemon.returncode}")
                if Path(endpoint).is_socket():
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError("ubusd did not create its local socket")
            # Real client/server protocol round-trip over AF_UNIX, not a
            # link-only or synthetic source inspection.
            command([str(root / "ubus"), "-s", endpoint, "-t", "3", "list"])
            print("SBAT6_NATIVE_MUSL_UBUSD_UBUS_LOCAL_IPC_RUNTIME_PASS")
            # The pinned ubusd ACL deliberately denies unprivileged event
            # publishing when no root-owned ACL grant is installed. Keep
            # the smoke rootless and assert this default-deny behavior.
            denied = subprocess.run(
                [str(root / "ubus"), "-s", endpoint, "-t", "3",
                 "send", "sbat6.local.smoke", '{"safe":true}'],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                timeout=5, check=False,
            )
            if denied.returncode != 6 or "Permission denied" not in denied.stderr:
                raise RuntimeError("unexpected unprivileged ubus send ACL result: "
                                   + str(denied.returncode) + " " + denied.stderr[-300:])
            print("SBAT6_NATIVE_MUSL_UBUSD_DEFAULT_DENY_ACL_RUNTIME_PASS")
            # Parse only the packaged loopback UCI configuration. No writes.
            shown = command([str(root / "uci"), "-c", str(config), "show", "network"])
            if "network.loopback" not in shown or "127.0.0.1" not in shown:
                raise RuntimeError("UCI did not parse packaged loopback policy")
            print("SBAT6_NATIVE_MUSL_UCI_LOOPBACK_READ_RUNTIME_PASS")
        finally:
            if daemon.poll() is None:
                daemon.terminate()
                try:
                    daemon.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    daemon.kill()
                    daemon.wait(timeout=3)
    print("LIMIT: no procd PID1, netifd, network interface, AP or Air6 hardware runtime")


if __name__ == "__main__":
    try:
        if len(sys.argv) != 3:
            raise ValueError("usage: smoke-arm64-musl-ipc.py ROOTFS_TAR_GZ MANIFEST_JSON")
        smoke(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            tarfile.TarError, json.JSONDecodeError) as error:
        print("SBAT6_NATIVE_MUSL_LOCAL_IPC_RUNTIME_FAIL", error, file=sys.stderr)
        sys.exit(1)
