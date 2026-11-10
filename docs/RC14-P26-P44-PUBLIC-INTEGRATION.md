# RC14-derived public P26/P44 extension integration

Scope: independently authored implementation based on observed **private RC14** A-slot boot,
p26 read-only SquashFS and p44 ext4 persistent overlay. No private binary, device dump,
credential, calibration, OEM source or signature material is imported.

## Manufacture

The native OpenWrt p26 job runs `install_p44_extension.py` inside the **same fakeroot
metadata namespace** after `package/install` and the locked-root shadow edit, before
packing and independent readback. It stages an S99 OpenWrt init.d unit and a standalone
runner. The script does **not** create, mount, format, resize or prepopulate p44.

## First boot / extension contract

P26 boots its normal services even when p44 is absent, unreadable or uninitialized.
After basic init, the late S99 unit checks for a mounted ext4 `/overlay`. It only
executes `/overlay/air6/boot.sh` when `/overlay/air6/enabled` exists. Both files
are owner-provisioned; no default active extension is shipped. A missing extension is
the intentional no-op (`exit 0`) state.

To execute, directory, enabled marker and executable must be root:root and have one
of the runner's conservative permission modes. The script must be executable,
must not be a symlink, and is given a 15-second timeout. Failures are logged
best-effort and never propagate to OpenWrt init. This is a development hook,
not an isolation boundary against a malicious root user.

The provisioner must separately initialize an empty p44 filesystem and must never
erase an existing owner overlay or secrets. The hook is not responsible for
initial overlay creation. Any p44 partition identity hardening, boot timing, hotplug
tests and hardware verification remain **unproven**.

## Evidence and limitations

- Private RC14 observation: A boot reached interactive UART with p26 SquashFS and
  p44 ext4 mounted read-write. This is not proof the new public p26 image boots.
- Public checks: install script unit tests and shell syntax checks.
- P25 boot-v2 section packing and full 32 MiB readback are separate unfinished gates.
- P26 acceptance still requires successful actual source-built pack and independent
  128 MiB SquashFS readback on exact branch HEAD. No signature, flash or RF action.

Provenance: independently authored MIT source from owner observations. OpenWrt
init.d conventions are interface behavior; no private implementation copied.
