# Pinned OpenWrt core Makefile byte audit (2026-10-31)

**Scope: read-only source inspection for Issues #21 and #4. No package build, rootfs, kernel ABI verification, device access, or legal approval.**

## Evidence and method

At the exact public `openwrt/openwrt` Git commit
`5700101d7c85381889d890dc1d3d001d0b4b6446`, six upstream Makefiles
were fetched as text from `raw.githubusercontent.com/openwrt/openwrt/<commit>/<path>`
on 2026-10-31 UTC. For each response, the UTF-8 bytes were independently
hashed with the Git blob-object formula:

`SHA1(b"blob " + ascii_decimal(byte_length) + b"\0" + file_bytes)`

The results were compared with `config/sbat6-userspace-source.json` and the
hard-coded selection in `tools/build/check_air6_userspace_source.py`.
All six **byte-derived Git blob IDs matched**. No upstream source was executed,
no binary assets were fetched, and no repository/device state was modified by
this read-only inspection.

| Package | Upstream path at pinned commit | Bytes | Recomputed Git blob SHA-1 | Result |
| --- | --- | ---: | --- | --- |
| base-files | `package/base-files/Makefile` | 9456 | `910a3daa3fa545453e72423b463c1781078d9e8b` | MATCH |
| busybox | `package/utils/busybox/Makefile` | 5076 | `a950cfff73a340df24c61353b0a68784fdbc0fb4` | MATCH |
| procd | `package/system/procd/Makefile` | 4621 | `21868ce6b1e7beb708d6059fefdd113d1128f229` | MATCH |
| ubus | `package/system/ubus/Makefile` | 1937 | `716f993b56ff0c256727c9645e13e12256a2410c` | MATCH |
| uci | `package/system/uci/Makefile` | 2140 | `11f89b0b15a966f6cd3d3098cfdbcff706923dd0` | MATCH |
| netifd | `package/network/config/netifd/Makefile` | 1306 | `d9479102ad9da067b963dcf7d889436e33ae5f8d` | MATCH |

## Reproduction and strict limits

The pinned paths, commit and expected digests are public and reviewable in the
[userspace source manifest](../config/sbat6-userspace-source.json). An
independently obtained local OpenWrt source tree can be checked **without
network, Git execution, or build** using:

```sh
python3 tools/build/check_air6_userspace_source.py --source-tree /path/to/openwrt
```

That local command is a separate optional check. **This audit did not run that
command against an independently obtained complete checkout.** The GitHub-hosted
CI continues to validate the manifest and synthetic tests; it does not fetch
these six upstream Makefiles or independently verify the upstream commit.

The fetched text and commit metadata were served by GitHub's mirror/CDN.
A matching SHA-1 is a Git object identity check, **not** a trusted signature,
canonical-origin verification, collision-resistant authenticity guarantee, or
rights/redistribution clearance. It does not establish the identity of the
*whole* upstream tree, feeds, dependencies, toolchain, kernel ABI, or build
outputs. All source rights remain **pending**. The LG6851F donor's Android/F2FS
image recipes, binary firmware, EEPROM/calibration and signing materials are
not part of this audit.

**Next gate:** verify canonical upstream commit/tree and five feed objects,
package dependency closure and rights, then build an independent noninstallable
SBAT6 userland in an isolated non-root environment. Keep #21 and #4 OPEN.
