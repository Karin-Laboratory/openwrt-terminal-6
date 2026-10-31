# Five pinned OpenWrt feed commit/tree object audit (2026-10-31)

**Scope: read-only source identity inspection for #21 and #4. This is not a canonical-origin audit, content-byte rehash, package build, rights approval or SBAT6 firmware verification.**

## Method and observed GitHub mirror objects

At the five immutable revisions already present in [`config/feeds.lock`](../config/feeds.lock), the GitHub REST Git-object API was queried on 2026-10-31 (JST) for `openwrt/{packages,luci,routing,telephony,video}`. Each `git/commits/<locked-sha>` response reported the exact requested commit ID, one parent and a root tree SHA. Each corresponding `git/trees/<tree-sha>` endpoint independently returned that exact root tree ID with `truncated=false`. The table records the **reported Git object metadata**, not a recomputation of object hashes from raw Git bytes.

| Feed | Locked commit SHA-1 | Reported root tree SHA-1 | Parent SHA-1 | Root entries |
| --- | --- | --- | --- | ---: |
| packages | `11396c3434272b73294d29aa9d86497b25cf33da` | `1abd824e12b18302572254ec0caffa6f4dc34d34` | `259eb5fc32cd6ad62406868e3cfc165a7f240aaa` | 19 |
| luci | `a8c110bed82375b69eb3881b2e54e617520e8c7d` | `c62ac511b11737e28cef7298d0533d6f1df3f93a` | `1c73e2ef538719f405aa2291088cf83dded8fd5e` | 21 |
| routing | `4b9891b9136259f93294a424507ed24c5e8c1cbd` | `73aada2640ec15608d4bc3dc05fb5eaf009f34ca` | `925146d29bebe389d4e071ed92da6bd485c54feb` | 14 |
| telephony | `5d68d53c160a325ea9d03fce393e051573bcc736` | `5993343af44fb2eff7621f4e3da2549dbc753d4b` | `4d8d33a023b24c52cd9443b9dc201fbdfe9c6aef` | 5 |
| video | `644a66261288b4a95dbc6e46fe805d33cb9f71d9` | `32f2324f3fc85de1725e89f55183aa9dc46075a8` | `0de25e3bdd23af4c5fe07950b7c23d7ea10deb7a` | 6 |

All five commit endpoints and five root tree endpoints responded with matching identifiers; **5/5 metadata lookups passed**. The tree entry counts are for the immediate root only, not recursive inventory. These feed revisions remain unchanged; no packages or source files were downloaded or executed.

### Reproduce the read-only lookup

For each feed and commit listed above, query the public endpoints below with the corresponding exact 40-character IDs:

- `https://api.github.com/repos/openwrt/<feed>/git/commits/<locked-commit>`
- `https://api.github.com/repos/openwrt/<feed>/git/trees/<reported-root-tree>`

Compare `sha`, `tree.sha` and `parents[].sha` from the commit response and `sha`, `truncated`, `tree.length` from the root-tree response. No authentication secrets, scripts, Git checkout, feed installation, image generation or hardware access are needed for this lookup.

## Explicitly unverified gates

1. **Canonical origins:** these are GitHub's OpenWrt organization mirror responses only. Exact commit/tree object reachability and byte identity at `git.openwrt.org` for packages/luci/routing/telephony, and any independent origin for video, were **not** established. Direct canonical commit pages could not be retrieved in this inspection; do not infer mirror equivalence. Full raw Git object rehash and signature/trust checks are also outstanding.
2. **Complete contents:** only root tree metadata was retrieved, not recursive trees, feed package Makefiles, dependency closure, build inputs or license notices. No feed or package content integrity, buildability or redistribution permission is established.
3. **SBAT6 integration:** no distinct SBAT6 OpenWrt target, rootfs, kernel ABI match, `dtbs_check`, modem runtime, device boot or safe recovery was tested. All existing `rights_review` statuses remain pending.

**Next gate:** compare the exact commit and root tree IDs with independently obtained canonical Git objects (without executing source), then review feed/package rights and dependency closure before considering an isolated noninstallable userspace build. Keep #21 and #4 OPEN. This audit is independent of GitHub-hosted source-only CI and is **not rerun by that CI**.

## Optional offline raw Git-object verification (2026-10-31)

A separate [read-only local checker](../tools/build/verify_feed_git_objects.py) now makes the next **byte identity** gate reproducible without fetching or executing third-party source. After obtaining **five local bare Git repositories through independently assessed sources**, supply each Git directory explicitly:

```sh
python3 tools/build/verify_feed_git_objects.py \
  --repo packages=/path/to/packages.git \
  --repo luci=/path/to/luci.git \
  --repo routing=/path/to/routing.git \
  --repo telephony=/path/to/telephony.git \
  --repo video=/path/to/video.git
```

The tool uses read-only `git cat-file` to retrieve the pinned commit and root tree **raw object bytes**, recomputes their Git SHA-1 object identities, and checks that each commit references its recorded root tree. It rejects missing feeds/objects, mismatched bytes or tree relationships, and symlinked Git-directory arguments. Git replacement objects are disabled. It does **not** clone, fetch, checkout, install, build, sign or touch a device.

**Current evidence boundary:** GitHub-hosted CI runs **synthetic local Git-object regression fixtures only**, not the five actual feed repositories. No actual canonical `git.openwrt.org` byte verification has been completed by this addition. The origin and transport of any supplied local Git directories must be assessed independently; feeding the checker a GitHub-mirror clone does **not** establish independent canonical-origin trust. Checking only the root commit/tree objects does not validate recursive blobs, dependency closure, package licenses, Git signatures, firmware safety or build reproducibility. All rights decisions remain pending and Issues #21/#4 remain open.
