# RC14-derived public P26/P44 extension integration

Scope: independently authored implementation based on observed **private RC14** A-slot boot,
p26 read-only SquashFS and p44 ext4 persistent overlay. No private binary, device dump,
credential, calibration, OEM source or signature material is imported.

## Manufacture

The native OpenWrt p26 job runs `install_p44_extension.py` inside the **same fakeroot
metadata namespace** after `package/install` and the locked-root shadow edit, before
packing and independent readback.
The native job also checks the installed init.d runner files are regular root:root
0755 files, verifies the S99 symlink target, checks the optional disable/timeout
contract, and refuses a pre-activated P44 extension before packing. The full
P26 independent rootfs readback subsequently compares these installed files. It stages an S99 OpenWrt init.d unit and a standalone
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

The public first-stage initramfs first checks p44 as `ro,noload`, without journal
replay. It accepts a recognized existing overlay unchanged. For a genuinely empty
ext4 filesystem (allowing only an empty `lost+found`), it then remounts p44 read-write
and creates only the required `upper/`, `work/`, `.fs_state -> 2`, and versioned
readiness markers. It never runs `mkfs`, `fsck`, truncates, or removes data. An exact,
recognized interrupted initialization can resume; any other non-empty or partial
state fails closed. The first read-write ext4 mount may perform normal journal
recovery if the filesystem needs it; that is distinct from formatting or an explicit
repair utility. The hook is not responsible for p44 formatting. Any p44 partition
identity hardening, boot timing, hotplug tests and hardware verification remain
**unproven**.

## P26 independent post-production attestation

The P26 producer intentionally marks its provisional JSON receipt
`P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK`, even if its own prefix/padding
checks pass. The separate `verify_p26_independent.py` now supports
`--producer-receipt` and `--attestation` arguments. Only after full 128 MiB
prefix/padding readback and extraction/inode/mode/owner/xattr/hardlink comparison
succeeds does it issue a **new**, exclusive-creation JSON receipt with status
`P26_INDEPENDENT_FS_READBACK_VERIFIED`.

The new attestation binds the full P26 SHA-256, SquashFS SHA-256/length,
and the producer receipt SHA-256, and explicitly states that physical boot,
LK acceptance, radio behavior and publication rights are not proven. Native
CI compares both receipts before printing
`PUBLIC_MT6990_REAL_SOURCE_BUILT_P26_INDEPENDENT_READBACK_PASS`.
It does not mutate the provisional receipt, sign or upload either image.

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
