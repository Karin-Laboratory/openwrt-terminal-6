# SBAT6 procd/netifd boot-stage policy (research only)

This directory is **input to the noninstallable ARM64 musl rootfs/initramfs build**, not an installable firmware profile. All four files are embedded byte-for-byte into the rootfs stage and the same Linux Image initramfs. No OEM data, radio firmware, credentials, signed image or hardware operation is involved.

The pinned upstream procd `initd/preinit.c` executes `/bin/sh /etc/preinit`, then transitions to `/sbin/procd`. The pinned procd `inittab.c` recognizes `sysinit`, while `rcS.c` invokes executable `/etc/rc.d/S*` entries with the `boot` argument. The `S10netifd` script asks procd's ubus `service add` API to supervise the **real** `/sbin/netifd` ELF already built in #98/#99. The inittab's `/etc/init.d/rcS` string is only a conventional placeholder: this pinned procd implementation dispatches via its built-in rcS function rather than executing that string.

The default `/etc/config/network` contains **loopback only**. There is no Ethernet uplink, DHCP server/client, Wi-Fi, NAT, login shell, root password or SSH configuration. This prevents an unreviewed interface from becoming remotely reachable by default. Nothing here demonstrates a working AP or runtime service; no PID1 execution has been performed.

**Still missing:** proof of actual procd→ubusd→sysinit→netifd startup, netifd UCI runtime dependencies, independent SBAT6 OpenWrt target, safe SSH provisioning, Ethernet and Wi-Fi/AP integration, persistent storage, cold-boot evidence and rights/release review. The historical private 2.4/5 GHz AP success remains separate from this public-source build.
