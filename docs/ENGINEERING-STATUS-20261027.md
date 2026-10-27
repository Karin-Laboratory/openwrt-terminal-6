# Integration status and next concrete build gate (2026-10-27)

**The source repository is Public as of 2026-10-27; it is not a complete SBAT6 firmware.** Development continues with a separate clean public Git history and retained Private research archives. Public visibility is a maintainer decision, not evidence that all source-rights, security or firmware-release gates have passed.

## Technical integration matrix

| Track | Verified | Source available in this public repository | Next proof required |
| --- | --- | --- | --- |
| A/B slot | Historical priority observations | Sanitized read-only state and competing LK retry models | Real LK retry/fallback transitions, independent recovery |
| Signing | Research-only historical accepted image | Local SHA-256 artifact verification only; no keys, SDK or signing tool | Rights/legal review and safe independently authenticated artifact pipeline |
| Linux kernel | Historical development Linux 6.18.44 boot; generic upstream object compiles | MediaTek Ethernet RFCs, Stage10 MED DMA delta | Full rights-cleared MT6990 source, board DTS, cross-compiled ARM64 kernel |
| Device Tree | MAC1, SGMII1, MT7531 observational evidence | GPL disabled-only experimental overlay + negative tests | providers for clock/reset/PHY/power, dtc/dtbs_check, cold-boot |
| OpenWrt userland | Procd and shell historically operated on device | Four pinned donor source-text blobs only (explicitly NOT LG6851F firmware build) | independent SBAT6 profile, feeds lock, packages, complete rootfs |
| Ethernet | Development-device packet transfer; [v2 ARM64 object build success](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40443738043) | RFC patches and static/host checks | complete kernel integration and repeated unmanaged cold boot |
| Wi-Fi 7 | 2.4/5 GHz data; 6 GHz AP started historically | Hardware identification only, no device calibration or OEM radio binary | licensed runtime, outside 6 GHz association, EHT/MLO, reboot persistence |
| Cellular modem | Stage9B/10 OpenWrt **LTE IPv4** packet data and TLS HTTPS verified | GPL Stage10 DMA delta, source SHA evidence, synthetic modem model | complete RIL/CCCI/MIPC/netifd userland and kernel, NR/IPv6 separately |
| Public source | New Git history and source catalog; repository now Public | Limited static checks completed; rights labels remain pending | comprehensive history, Actions/PR logs, source rights and security governance |
| Firmware release | NONE | NONE | complete safe build, first-boot credentials, actual fallback and secure release provenance |

## Isolated self-hosted evidence

1. **PASS**: The archived v2 Private, trusted, source-equivalent Ethernet object build [run #40443738043](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40443738043) compiled pinned Linux v6.18 MediaTek Ethernet baseline, RFC1, RFC1+RFC2 on ARM64; no firmware image produced.
2. [Generic upstream ARM64 `Image` smoke run #40444627122](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40444627122) started in a Private non-root isolated workflow. **Not an SBAT6 kernel**; outcome must be read from its completed Actions job before claiming PASS.
3. [Synthetic clean-source test mirror run #40445484403](https://github.com/Karin-Laboratory/archive-openwrt-terminal-6-v2/actions/runs/40445484403) uses 19 file contents pinned to the clean repo. Its outcome must likewise be checked from completed job steps.
4. The public repository's trusted self-hosted workflow now requires manual dispatch, main and a Private-repository guard; it must not run on this Public repository. Older queued jobs were identified during the cutover review, but their current cancellation status has not been established by this document. Home infrastructure privileges and signing keys are not intentionally supplied.

## Recent source-only migration steps

- Independently selected [SGMII1 disabled overlay and board metadata](../board/README.md) from Private v1, not OEM decompiled DTS or firmware. New lexical safety tests require the fragments stay disabled.
- Verified actual public [OpenWrt MT6990 donor](OPENWRT-DONOR-SOURCE.md) commit `a40df9a5afb46716dea799acea69f17480df4d82`, and identified **LG6851F-specific** Android boot and `boot_b.img`/`rootfs_b.img` recipes that must not be used for SBAT6. The restricted inspection script fetches four hash-pinned text blobs only.
- The source catalog is expanded and fail-closed for uncatalogued DTS/DTSI/MK, disallowed binary artifacts and symlinks. For the current authoritative count, inspect `config/source-catalog.json`; rights review remains pending.
- Prior [branch-tip and PR-text audit](PREPUBLICATION-REF-AND-BUILD-AUDIT-20261027.md) covered 13 branch-tip trees and 82 distinct blobs with no high-confidence sensitive pattern matches. Separately the available **47 new main commit diffs** were checked with high-confidence patterns and no matches, but neither coverage proves all intermediate objects, CI logs and external copies are clean.

## Hard stop conditions

Do not equate Public visibility with release clearance. Do not flash or sign firmware, link an unaudited home runner to untrusted external PRs, publish exploit instructions, mirror SDK keys, ship per-device radio calibration, or claim NR/EHT/MLO/fallback until each independent verification gate is satisfied. Source release and flashable firmware release remain separate decisions.
