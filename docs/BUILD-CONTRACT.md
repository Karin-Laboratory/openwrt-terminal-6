# Reproducible build input catalog, source-only stage

The machine-readable [source catalog](../config/source-catalog.json) pins **individual source files** (Git blob identities) for Ethernet RFCs, Stage10 MED DMA code, A/B research and the synthetic modem transport model.

This is a reproducibility *contract for the files present here*, not a complete firmware Bill of Materials or a signature. The catalog intentionally records rights review as PENDING and lists missing components rather than fabricating OpenWrt firmware build success.

## Modes

- `python3 tools/build/verify_source_catalog.py`: verify local source bytes, names, file type, origin, license labels and the prohibition on flashable payload content in this catalog. A PASS means **source identity/schema only**.
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

The previous historical firmware configuration and private device images must not be copied here, even to make this build appear complete.
