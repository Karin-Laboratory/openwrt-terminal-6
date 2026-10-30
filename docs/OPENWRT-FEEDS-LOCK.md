# Pinned upstream OpenWrt feed snapshot, source-only

**Status: five feed source commits selected, not yet a complete SBAT6 build.**

The public donor's `feeds.conf.default` listed five **floating** source feeds (packages, luci, routing, telephony, video). They are inappropriate as reproducible build inputs because each may change without any change to the SBAT6 repository.

This project now retains [config/feeds.lock](../config/feeds.lock), with a proposed five-source snapshot at **2026-09-09 15:04:35 UTC**, the independently inspected public donor commit time. The precise commit IDs were obtained from the official OpenWrt organization's GitHub repositories' histories using a fixed `until` query.

| Feed | Official GitHub source history | Pinned commit |
| --- | --- | --- |
| packages | [openwrt/packages](https://github.com/openwrt/packages) | `11396c3434272b73294d29aa9d86497b25cf33da` |
| luci | [openwrt/luci](https://github.com/openwrt/luci) | `a8c110bed82375b69eb3881b2e54e617520e8c7d` |
| routing | [openwrt/routing](https://github.com/openwrt/routing) | `4b9891b9136259f93294a424507ed24c5e8c1cbd` |
| telephony | [openwrt/telephony](https://github.com/openwrt/telephony) | `5d68d53c160a325ea9d03fce393e051573bcc736` |
| video | [openwrt/video](https://github.com/openwrt/video) | `644a66261288b4a95dbc6e46fe805d33cb9f71d9` |

The [feed-lock verifier](../tools/build/verify_feeds_lock.py) rejects missing or non-40-character revisions, **any full-length commit substituted for one of the five reviewed snapshot IDs**, insecure/credentialed URLs, unknown hosts and arbitrary local feeds, unexpected feed names and duplicates. A different feed commit requires an explicit review and matching update to the verifier and its regression tests; passing this source-only check is not a license or origin-authenticity finding. Run it read-only:

`python3 tools/build/verify_feeds_lock.py config/feeds.lock`

GitHub-mirror history is **not yet proof** that all five specific Git objects are accessible on their `git.openwrt.org` canonical remotes or that all packages can legally be redistributed. Before real feeds installation, verify each exact object against the canonical Git host and perform the package/firmware license review. The pin is a proposed repeatable source snapshot, not a signed release.

**Do not** execute a generic donor `make` image recipe. Its LG6851F configuration contains model-specific boot/rootfs packaging and firmware binaries not cleared for SBAT6. The only donor files automatically retrieved by this clean repository are the four individually vetted text files through the [restricted inspection tool](../scripts/fetch-pinned-openwrt-donor.sh).

Separate outstanding work: rights-cleared full OpenWrt buildroot, distinct SBAT6 `target/linux` profile and DTS, OpenWrt package ABI, kernel compatibility and repeatable rootfs without any signing, radio EEPROM or flashable image generation.
