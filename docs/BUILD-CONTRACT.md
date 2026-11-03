# Reproducible build input catalog, source-only stage

> The legacy `SOURCE_ONLY` catalog schema describes what may enter public Git history, **not a ban on locally or ephemerally building unsigned p25/p26**. Public CI must not upload built images/intermediates into artifacts, caches, Releases or registries; see [workflow policy](../tools/security/check_workflows.py). Actual image distribution requires the applicable GPL corresponding source/notices and third-party license rights.


> **Development vs release (2026-11-04):** Follow the [current p25/p26 mainline policy](MAINLINE-P25-P26-POLICY.md) for work selection. The catalog's pending rights labels and the optional `--public-source` / `--public-build` completeness modes do **not** prohibit local engineering, independently authored observation-based implementations, or building and testing unsigned p25/p26. Preserve OpenWrt-standard licensing and check redistribution obligations before externally releasing images. Historical source-only coverage is not a mandate to avoid implementing real image production.


The [dated branch-tip and ARM64 build evidence](PREPUBLICATION-REF-AND-BUILD-AUDIT-20261027.md) records one verified upstream Ethernet object compile on the separate Private v2 runner, not a complete firmware build. The machine-readable [source catalog](../config/source-catalog.json) pins catalogued source, unit-test, board-overlay and build-helper files (Git blob identities) for Ethernet RFCs, Stage10 MED DMA code, A/B research and the synthetic modem transport model.

The checker also fails when a source/test/Makefile/shell file exists in the covered directories without a catalog entry. The initial 27-path snapshot was checked against a complete GitHub tree on 2026-10-27. Later reviews expanded coverage; use the current catalog for the authoritative inventory. This is a reproducibility *contract for catalogued files present here*, not a complete firmware Bill of Materials or a signature. The catalog intentionally records rights review as PENDING and lists missing components rather than fabricating OpenWrt firmware build success.

## Modes

- `python3 tools/build/verify_source_catalog.py`: verify local source bytes, names, file type, origin, license labels and the prohibition on flashable payload content in this catalog. A PASS means **source identity/schema only**.
- `python3 tools/build/verify_source_catalog.py --public-source`: checks each recorded source entry's explicit `rights_review=approved` along with source schema and byte identities, **without demanding a complete firmware image**. Currently expected to FAIL as rights reviews remain pending. A PASS would be an internal label check, not legal clearance or permission to publish.
- `python3 tools/build/verify_source_catalog.py --public-build`: additional hypothetical completeness check, currently expected to **FAIL** because independent contributor-rights approval and complete build/runtime inputs are unavailable. Even passing this mode alone never authorizes publishing a flashable binary.

Input identity uses the standard Git object SHA-1 content identifier, calculated on `blob <length>\0<bytes>`. Git blob IDs are not authenticated release signatures or strong external supply-chain attestations. For a future release, pin upstream commits and SHA-256 digests of legally obtained independent source archives, verify source ownership and produce an authenticated build manifest.

## Component boundaries

| Component | Source capability in new repository | Required before public independent firmware |
| --- | --- | --- |
| Boot A/B | Synthetic observation + retry hypothesis models | Device-verified LK retry/fallback and independent rescue |
| Signing | No keys or signatures included | Lawful SDK sourcing, private vendor coordination and independent safety review |
| Kernel | Limited GPL Linux v6.18 RFC and experimental Stage10 delta | Rights-cleared complete MT6990 Linux, DTS, clocks/reset/PHY and drivers |
| OpenWrt userland | Host-side models only | Pinned buildroot, feeds, rootfs, packages and daemon lifecycle |
| Ethernet | Two upstream-review RFC deltas and one experimental FE/MED fix | Clean ARM64 build and repeated cold-boot device traffic |
| Wi-Fi 7 | Historical 6 GHz AP startup observation only | Legally distributable firmware, verified client/6 GHz/EHT/MLO behavior |
| Modem | Recovered Stage10 LTE IPv4 source evidence and synthetic state machine | Rights-cleared transport/RIL/data runtime; NR and IPv6 each separately proven |

Source identity verification and complete reproducibility are separate from **permission to redistribute**. Do not promote a component status simply because synthetic tests pass or its byte hash matches research evidence.

The board SGMII1 overlay is disabled-only and not part of a bootable DTB. The previous historical firmware configuration and private device images must not be copied here, even to make this build appear complete.

## Source code release and firmware delivery are separate gates

A verified source-only build input and documented redistribution approval can potentially support a source repository release before all hardware features operate. The `--public-source` gate deliberately does *not* require a full kernel, NR data call, firmware signing or fallback. The separate `--public-build` mode requires complete build dependencies and remains blocked. Both checks are only pieces of the full GitHub/third-party-rights/security review, never a substitute for independent distribution-rights review or safe firmware release approval.

## Pinned feeds are now a checked prerequisite

The independently recorded [OpenWrt feed snapshot](OPENWRT-FEEDS-LOCK.md) contains five fixed Git commit IDs. `tools/build/verify_feeds_lock.py config/feeds.lock` rejects mutable feed branches, local source references, arbitrary hosts and credentials. This is a reproducibility preflight, **not** an OpenWrt rootfs build or a license review. The canonical `git.openwrt.org` remotes still require independent reachability confirmation of these Git objects.
