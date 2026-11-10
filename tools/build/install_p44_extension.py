#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Install independently authored P44 extension hook into an OpenWrt p26 staging root.

Never formats, mounts, or reads p44 during manufacture. No secrets or firmware.
Run in the same fakeroot namespace as package/install, before p26 packing.
"""
import argparse
from pathlib import Path
import os

INIT = """#!/bin/sh /etc/rc.common
# SPDX-License-Identifier: MIT
# Late noncritical extension; failures must not prevent normal boot.
START=99
STOP=01

start() {
    /bin/sh /usr/libexec/air6/p44-extension-runner || :
}
"""
RUNNER = """#!/bin/sh
# SPDX-License-Identifier: MIT
# Independently authored from observed p44 overlay behavior, not OEM source.
# All exits are nonfatal to OpenWrt service startup.
log() { logger -t air6-p44 -- "$1" 2>/dev/null || :; }
base=/overlay/air6
script=$base/boot.sh
# Do not guess a missing ext4 partition or initialize existing data.
grep -q ' /overlay ext4 ' /proc/mounts 2>/dev/null || exit 0
[ -d "$base" ] && [ ! -L "$base" ] || exit 0
[ -f "$base/enabled" ] && [ ! -L "$base/enabled" ] || exit 0
[ -f "$script" ] && [ ! -L "$script" ] && [ -x "$script" ] || exit 0
# Only root-owned, non-group/world-writable components can authorize execution.
for part in "$base" "$base/enabled" "$script"; do
    [ ! -L "$part" ] || { log 'unsafe symlink'; exit 0; }
    uid=$(stat -c %u "$part" 2>/dev/null) || exit 0
    gid=$(stat -c %g "$part" 2>/dev/null) || exit 0
    mode=$(stat -c %a "$part" 2>/dev/null) || exit 0
    [ "$uid:$gid" = 0:0 ] || { log 'unsafe owner'; exit 0; }
    # Strict allowlist avoids platform-specific octal arithmetic.
    case "$mode" in 700|500|400|600|750|550|755|555|644|744) : ;;
        *) log 'unsafe mode'; exit 0 ;;
    esac
done
command -v timeout >/dev/null 2>&1 || { log 'timeout unavailable'; exit 0; }
timeout 15 "$script"
status=$?
[ "$status" -eq 0 ] || log "extension exited status=$status"
exit 0
"""

def install(root: Path) -> None:
    if root.is_symlink() or not root.is_dir() or root.resolve() == Path("/"):
        raise ValueError("unsafe staging root")
    for rel in ("etc", "etc/init.d", "etc/rc.d", "usr", "usr/libexec", "usr/libexec/air6"):
        p = root / rel
        if p.is_symlink():
            raise ValueError("symlink staging directory: " + rel)
        p.mkdir(parents=True, exist_ok=True)
    for rel, content in (("etc/init.d/air6-p44-extension", INIT),
                         ("usr/libexec/air6/p44-extension-runner", RUNNER)):
        target = root / rel
        if target.exists() or target.is_symlink():
            raise ValueError("refuse to overwrite " + rel)
        target.write_text(content)
        target.chmod(0o755)
    # OpenWrt's init.d convention, with a late S99 service and no network dependency.
    link = root / "etc/rc.d/S99air6-p44-extension"
    if link.exists() or link.is_symlink():
        raise ValueError("service link exists")
    link.symlink_to("../init.d/air6-p44-extension")
    print("P26_P44_NONCRITICAL_HOOK_STAGED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("rootfs", type=Path)
    install(parser.parse_args().rootfs)
