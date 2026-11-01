# First-boot management credentials: AP-first research policy

**Status: design only (2026-11-01).** Tracks [#21](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/21), [#74](https://github.com/Karin-Laboratory/openwrt-terminal-6/issues/74), and the [release gates](RELEASE-GATES.md).
This document is not a command to create a signed or installable image.

## Invariants

- Current source-only stage deliberately has `root:!` in `/etc/passwd` and a dedicated locked `ubus` service account. Do not replace these with a shared/empty root password or a development backdoor.
- The public GitHub-hosted ARM64/QEMU smoke tests **must not require personal keys** or offer an SSH listener; they run with no external network. A QEMU PASS proves no authentication and no Air6 connectivity.
- In any **future separately authorized private device image**, start Dropbear only after explicit owner management provisioning. Fail closed if no valid administrator public key exists. Do not infer credentials from device serials, factory fields, or private archives.
- Never package SSH *private* keys, reusable Dropbear *host private* keys, tokens, factory MAC/EEPROM/calibration or OEM secrets into source, GitHub Actions logs, manifests, images, or reusable build caches.
- Review full source rights, rescue access, rollback and the owner-operated hardware test gate independently. This policy alone does **not** authorize release, signing, or flashing.

## Proposed management provisioning interface (not implemented)

1. For a future local build/provisioning command, the owner provides a path to a single **OpenSSH public key** or a restricted allowlist. Prefer `ssh-ed25519`. Validate the key type, syntax, length, lack of control characters and duplicates; require a restrictive target account/role and explicit management-network policy. Never read or transmit the private half.
2. For release-capable builds, **no key ⇒ fail the final image/provisioning gate**. For test-only generic/QEMU source builds, retain the credential-free stage; do not weaken CI or introduce placeholder accounts to satisfy this gate.
3. Stage the validated key only in an owner-controlled output/provisioning area with restrictive permissions and predictable ownership. Keep the original committed `root:!` and service accounts locked; document the separately approved key-only SSH account and filesystem location before implementing Dropbear startup.
4. Generate a fresh, device-local Dropbear **host key on first boot** using a secure random source and private writable storage; preserve across ordinary reboots. If entropy or writable storage is unavailable, do not start the SSH listener. Host key fingerprints are verification aids, not private credentials.
5. Bind SSH management only to the chosen trusted management interface after the kernel/DSA/bridge path has been verified. No default WAN-facing SSH listener; no shared password fallback. Verify key-only login, rejection of password authentication, authorization boundaries and persistence in the separately approved hardware acceptance test.
6. For recovery, establish an explicit owner-operated UART/offline provisioning path before any sign/flash milestone. A QEMU guest or an owner-specific historical A/B fallback is **not** guaranteed rescue for third parties.

## Required acceptance tests before enabling Dropbear in a device image

| Gate | Evidence | Explicit limit |
| --- | --- | --- |
| Source-only validator | Reject malformed/missing public keys, private-key-looking input, duplicates, injected newlines and world-readable provisioning output | Synthetic local fixtures only |
| Package/build | Correct OpenWrt Dropbear package, config and dependencies built from fixed OpenWrt buildroot/feeds; no vendor runtime or secrets | Not an SSH service test |
| Isolated runtime | No external NIC, no preset credential, no listener until an explicit test key is provisioned; authentication assertions with disposable test keys | Does not prove Air6 management reachability |
| Owner hardware gate | Secure first boot, unique host key, permitted-interface SSH, no password login, persistence and tested rescue | Separately approved, not CI/PR automation |
| Release/security | Audit, licensing, coordinated disclosure, independent recovery and signer review | Always blocked while open |

**Implementation sequencing:** first the noninstallable OpenWrt subtarget and its official `dropbear`/base-files packaging, then a separate narrowly scoped provisioning patch. Do not insert credentials in the current hand-built procd/netifd initramfs merely to obtain a green CI marker.
