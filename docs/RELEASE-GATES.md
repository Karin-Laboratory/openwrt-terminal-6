# Publication and firmware distribution are separate milestones

For the dated branch-tip, GitHub-conversation and source-equivalent ARM64 build review, see [2026-10-27 additional audit](PREPUBLICATION-REF-AND-BUILD-AUDIT-20261027.md). It is limited in scope and does not clear these gates.

## Source repository visibility: presently Private

Before switching to Public, verify all of the following independently:

- Every reachable Git object/commit/branch/tag and tracked file in **this** new-history repo contains only approved source and no private build-host endpoints, secrets, firmware images, exploitable unpublished vulnerability details or restricted third-party material.
- All PR/Issue text, reviews, Actions run logs/artifacts and old URL redirects are reviewed; an automated repository scanner does not cover those.
- Source and patch copyright, licenses, known third-party provenance, and contributor rights are checked per file.
- Any vendor security findings are coordinated confidentially; technical disclosure is evaluated separately from general OpenWrt source publication.
- GitHub branch protection, approved workflows, Actions permissions and private vulnerability reporting are configured.
- No home/self-hosted privileged runner is automatically targeted by external PRs; public PR CI uses isolated runners with minimal permissions.
- README capabilities and test status match reproducible evidence.

A prior experimental distribution exists outside this repository. Do not assume changing GitHub visibility can revoke or repair already distributed archives.

## Flashable firmware release: blocked even after source publication

Do **not** provide device-installable firmware, signed images, recovery commands or A/B write procedures until:

- Validated device revision, pinning of complete build inputs and legal runtime/firmware sources.
- Credential-secure first boot; no preconfigured shared or blank administrative password.
- Authenticated artifact provenance and reproducible release manifest.
- Proven cold-boot and failure/retry fallback, with a safe rescue process independently reviewed.
- Kernel/userland, Ethernet, Wi-Fi and modem stability, plus appropriate regulatory requirements.
- Separate verification of LTE, 5G NR, IPv6 and Wi-Fi 7 EHT/MLO before making each claim.

The lack of a firmware release is **not** a failure of source-only upstream research.

## CI trust boundary

Use GitHub-hosted, short-lived runners for source-only test jobs. No SDK keys, device access, preserved private build paths, firmware signers, shell access to home infrastructure or secret-backed upload actions are authorized in public PR workflows.
