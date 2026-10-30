# Air6 independent OpenWrt userspace source selection (2026-10-30)

**Scope: metadata and source verification only. NOT an OpenWrt rootfs, package build, image, or deployable SBAT6 target.**

- Upstream repository: `openwrt/openwrt` official GitHub mirror. Pinned development-main commit `5700101d7c85381889d890dc1d3d001d0b4b6446` observed by GitHub on 2026-10-30. This is a working *source inspection reference*, **not** a release recommendation or a proven MT6990 build base.
- Five existing feeds are fixed in [feeds.lock](../config/feeds.lock). Their commit IDs were selected earlier but canonical feed access and feed/package rights still need independent verification.
- Only a small proposed userland package inventory is frozen: base-files, BusyBox, procd, ubus, uci and netifd. No assertion that these packages/build dependencies currently compile together on MT6990.
- [Machine-readable source selection](../config/sbat6-userspace-source.json) deliberately rejects rootfs/image generation, signing and device writes, forbids preset root authentication, and retains `rights_review=pending`.
- Run `python3 tools/build/check_air6_userspace_source.py` for host-only validation. Synthetic negative tests cover floating revisions, malicious feeds, donor substitution, insecure defaults and accidental firmware enablement.

## Next implementation gates for #21

1. Verify the selected OpenWrt base and five feed Git objects against independently reachable official origins; review license and package distribution rights. Retain exact hashes and no binary donor checkout.
2. Add a real SBAT6-specific build target/config in a separate review PR. Establish kernel ABI, target identity and package closure without copying LG6851F Android/F2FS image recipes, calibration, radio firmware or signing data.
3. In isolated non-root CI, build a **noninstallable** package/rootfs staging tree with pinned compiler/inputs and SHA-256 manifest. The present contract explicitly does **not** authorize this step; review and change its scope in a separate PR with tests.
4. Prove safety/first-boot behavior and source rights; independently coordinate #20 DTS/driver integration, #22 modem transport and #2 publication before any device test or image release.

Passing this manifest gate is a stricter source-selection **preflight**, not #21 completion. Issue stays OPEN.
