# From research to upstreamable OpenWrt support

This is a staged **source-development** sequence, not a deployment checklist.

1. **Boot control and fallback model:** independently establish A/B metadata interpretation, failure counters and recovery semantics on a test harness. No slot-changing commands or signed boot modifications are supplied here.
2. **Boot-image trust and legal signing inputs:** document permissible SDK acquisition and redistribution conditions; compare image format and trust boundary with manufacturer disclosures in a confidential channel where appropriate. Do not publish keys or validated bypass procedures.
3. **MT6990 kernel and Device Tree:** isolate copyright-cleared common SoC drivers and binding providers. Pin an openly reproducible kernel baseline before attempting a clean ARM64 build.
4. **OpenWrt userspace:** pin buildroot, feeds, package ABI and complete rootfs config. Depend on legally sourced modem/radio runtime; do not substitute private rootfs copies.
5. **Ethernet:** review MediaTek workqueue teardown RFCs and Stage10 initial MED-DMA preservation separately. Prove stable link/traffic from repeated cold boots rather than relying on one successful rescue run.
6. **Wi-Fi:** verify 2.4/5 GHz connectivity, 6 GHz association and full Wi-Fi 7 EHT/MLO as independent milestones. Never distribute device-specific radio NV/calibration.
7. **Modem:** preserve proven historical LTE IPv4 Stage9B/10 source attribution; reproduce end-to-end radio/data with rights-cleared drivers and userland. Separately test NR and IPv6.
8. **Resilience and release:** test fallback, power loss, boot repeatability, hardware permissions, first-boot credentials and artifact signing with independent rescue before any general firmware package.

The first public milestone is **reviewable source and tests**, which can be shared without claiming a flashable product. An OpenWrt upstream merge requires separately reviewable kernel/SoC, board, userland and license-ready components.
