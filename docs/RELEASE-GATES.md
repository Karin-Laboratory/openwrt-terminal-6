# Publication and firmware distribution are separate milestones

Current track-by-track integration and self-hosted build evidence: [engineering status 2026-10-27](ENGINEERING-STATUS-20261027.md). Pending runs are not counted as PASS.

For the dated branch-tip, GitHub-conversation and source-equivalent ARM64 build review, see [2026-10-27 additional audit](PREPUBLICATION-REF-AND-BUILD-AUDIT-20261027.md). It is limited in scope and does not clear these gates.

The source-only rights-label subgate is `python3 tools/build/verify_source_catalog.py --public-source`; it is expected to **FAIL** while attribution/redistribution reviews are PENDING. This subgate does not require unfinished firmware features, but a PASS would not supersede the independent security and rights checklist below.

## Source repository visibility: Public since 2026-10-27

The maintainer elected to make this source-only repository Public on 2026-10-27. The following remain ongoing audit and remediation responsibilities; Public status **does not establish that every item has been cleared**:

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

## Queued trusted-runner safety condition (2026-10-27)

The clean repository's self-hosted source build was restricted to **manual workflow_dispatch + main + Private** after numerous push-triggered jobs queued without a registered runner. Any **previously queued jobs** created under the old trigger require review and cancellation where applicable, even though the repository has already become Public. Confirm real GitHub Actions queue/runner settings; this document does not certify that historical jobs are cleared. The review must be based on real administrative settings and completed records; the user-owned archived v2 runner's PASS does not establish clean-repo assignment.
