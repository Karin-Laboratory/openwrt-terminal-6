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
the intentional no-op (`exit 0`) state. Creating `/overlay/air6/disabled`
(disallowed if it is a symlink) overrides `enabled` and prevents execution.
Removing `enabled` also disables execution; neither action touches P26.

To execute, directory, enabled marker and executable must be root:root and have one
of the runner's conservative permission modes. The script must be executable,
must not be a symlink, and is given a 15-second timeout. The runner logs the start and exit status (including a timeout) best-effort,
without copying script standard output into a public build log. Failures never
propagate to OpenWrt init. This is a development hook,
not an isolation boundary against a malicious root user.

The provisioner must separately initialize an empty p44 filesystem and must never
erase an existing owner overlay or secrets. The hook is not responsible for
initial overlay creation. Any p44 partition identity hardening, boot timing, hotplug
tests and hardware verification remain **unproven**.

## Evidence and limitations

- Private RC14 observation: A boot reached interactive UART with p26 SquashFS and
  p44 ext4 mounted read-write. This is not proof the new public p26 image boots.
- Public checks: install script unit tests and shell syntax checks.
- Public P25 boot-v2 section packing and full 32 MiB *synthetic* independent
  readback tests exist; native Air6-compatible input configuration and boot
  acceptance remain unfinished.
- Base PR #127 recorded a genuine source-built 128 MiB p26 and independent
  SquashFS readback PASS on 2026-11-07 (SHA-256 `c55884a21dddac40569689b90c3911d3400092d652278b9deb8a009145b23c35`).
  The modified P44-hook tree requires a **new** exact-HEAD source-built pack and
  independent readback; the base receipt cannot be reused as its result. No signature, flash or RF action.

Provenance: independently authored MIT source from owner observations. OpenWrt
init.d conventions are interface behavior; no private implementation copied.
