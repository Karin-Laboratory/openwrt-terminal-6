# SBAT6 procd/netifd boot-stage policy (research only)

This directory is **input to the noninstallable ARM64 musl rootfs/initramfs build**, not an installable firmware profile. All six policy files are embedded byte-for-byte into the rootfs stage and the same Linux Image initramfs. No OEM data, radio firmware, credentials, signed image or hardware operation is involved.

The staged `/etc/passwd` and `/etc/group` now provide a dedicated locked `ubus` service identity (UID/GID 81), alongside a locked root account. Neither account has a usable login shell or password. The pinned procd `state.c` resolves `getpwnam("ubus")`, creates/chowns `/var/run/ubus`, and requests that the ubusd service run as that account. This is an **actual initramfs/rootfs input**, not evidence that privilege dropping or service startup has executed; UID/GID compatibility with a future native OpenWrt target still needs review. No SSH or remote management is enabled.

The pinned upstream procd `initd/preinit.c` executes `/bin/sh /etc/preinit`, then transitions to `/sbin/procd`. The pinned procd `inittab.c` recognizes `sysinit`, while `rcS.c` invokes executable `/etc/rc.d/S*` entries with the `boot` argument. The `S10netifd` script asks procd's ubus `service add` API to supervise the **real** `/sbin/netifd` ELF already built in #98/#99. The inittab's `/etc/init.d/rcS` string is only a conventional placeholder: this pinned procd implementation dispatches via its built-in rcS function rather than executing that string.

The default `/etc/config/network` contains **loopback only**. There is no Ethernet uplink, DHCP server/client, Wi-Fi, NAT, login shell, root password or SSH configuration. This prevents an unreviewed interface from becoming remotely reachable by default. Nothing here demonstrates a working AP or runtime service; no PID1 execution has been performed.

**Still missing:** proof of actual procd→ubusd→sysinit→netifd startup, netifd UCI runtime dependencies, independent SBAT6 OpenWrt target, safe SSH provisioning, Ethernet and Wi-Fi/AP integration, persistent storage, cold-boot evidence and rights/release review. The historical private 2.4/5 GHz AP success remains separate from this public-source build.

## Rootless native ARM64 IPC smoke

The hosted native AArch64 Image job runs `scripts/smoke-arm64-musl-ipc.py`
after producing the real static-musl rootfs stage. The script verifies the
archive and individual ELF identities, copies only `ubusd`, `ubus` and `uci`
into a private temporary directory, and executes an actual `ubusd`/ `ubus`
client/server lookup round trip over a local AF_UNIX socket and confirms\nthat unprivileged event publishing is denied by ubusd's default ACL. It also executes the
real `uci` CLI against the packaged loopback-only network configuration.
No root privileges, real interfaces, network namespace modifications,
flash, firmware, or installed system files are involved. Binaries are
removed after the test. A successful smoke is evidence of **userspace IPC
and UCI execution**, not procd PID1 transitions, netifd registration,
Ethernet/bridge, Wi-Fi AP, Air6 boot, or release rights. A failed smoke
blocks the PR rather than being reported as runtime PASS.
