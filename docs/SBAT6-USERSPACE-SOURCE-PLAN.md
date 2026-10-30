# Air6 independent OpenWrt userspace source selection (2026-10-30)

**Scope: metadata and source verification only. NOT an OpenWrt rootfs, package build, image, or deployable SBAT6 target.**

- Upstream repository: `openwrt/openwrt` official GitHub mirror. Pinned development-main commit `5700101d7c85381889d890dc1d3d001d0b4b6446` observed by GitHub on 2026-10-30. This is a working *source inspection reference*, **not** a release recommendation or a proven MT6990 build base.
- Five existing feeds are fixed in [feeds.lock](../config/feeds.lock). Their commit IDs were selected earlier but canonical feed access and feed/package rights still need independent verification.
- Only a small proposed userland package inventory is frozen: base-files, BusyBox, procd, ubus, uci and netifd. No assertion that these packages/build dependencies currently compile together on MT6990.
- On 2026-10-31, read-only GitHub API inspection of the official `openwrt/openwrt` repository at pinned commit `5700101d7c85381889d890dc1d3d001d0b4b6446` confirmed the commit tree `799d3a1ec74e3f442d211fc19c666ca60f50ec39` and the six package Makefile blob IDs below. The source-selection manifest now records their exact paths and Git blob IDs, and the offline checker rejects substitutions, omissions and extra records. This is a **record of inspected GitHub source identities**, not a fetch or re-hash of upstream bytes in CI, package dependency closure, a reproducible build, or redistribution approval.

| Package | Pinned upstream Makefile path | Git blob SHA-1 |
| --- | --- | --- |
| base-files | `package/base-files/Makefile` | `910a3daa3fa545453e72423b463c1781078d9e8b` |
| busybox | `package/utils/busybox/Makefile` | `a950cfff73a340df24c61353b0a68784fdbc0fb4` |
| procd | `package/system/procd/Makefile` | `21868ce6b1e7beb708d6059fefdd113d1128f229` |
| ubus | `package/system/ubus/Makefile` | `716f993b56ff0c256727c9645e13e12256a2410c` |
| uci | `package/system/uci/Makefile` | `11f89b0b15a966f6cd3d3098cfdbcff706923dd0` |
| netifd | `package/network/config/netifd/Makefile` | `d9479102ad9da067b963dcf7d889436e33ae5f8d` |
- [Machine-readable source selection](../config/sbat6-userspace-source.json) deliberately rejects rootfs/image generation, signing and device writes, forbids preset root authentication, and retains `rights_review=pending`.
- Run `python3 tools/build/check_air6_userspace_source.py` for host-only validation. Synthetic negative tests cover floating revisions, malicious feeds, donor substitution, insecure defaults and accidental firmware enablement.

## Next implementation gates for #21

1. Independently verify the selected OpenWrt base and five feed Git objects against canonical origins (GitHub mirror inspection alone is insufficient); verify the six pinned Makefile bytes and their dependency closure in a controlled checkout, then review package and source redistribution rights. Retain exact hashes and no binary donor checkout.
2. Add a real SBAT6-specific build target/config in a separate review PR. Establish kernel ABI, target identity and package closure without copying LG6851F Android/F2FS image recipes, calibration, radio firmware or signing data.
3. In isolated non-root CI, build a **noninstallable** package/rootfs staging tree with pinned compiler/inputs and SHA-256 manifest. The present contract explicitly does **not** authorize this step; review and change its scope in a separate PR with tests.
4. Prove safety/first-boot behavior and source rights; independently coordinate #20 DTS/driver integration, #22 modem transport and #2 publication before any device test or image release.

Passing this manifest gate is a stricter source-selection **preflight**, not #21 completion. Issue stays OPEN.
