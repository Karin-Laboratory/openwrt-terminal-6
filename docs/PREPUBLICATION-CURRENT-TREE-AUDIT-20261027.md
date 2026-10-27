# Prepublication current-tree and commit-metadata review (2026-10-27)

**Scope:** new clean-history repository only. **Visibility must remain Private.** This review does not authorize any public firmware release.

## Actual GitHub observations

- GitHub's recursive tree API returned **46 blobs**, total about **154 kB**, `truncated=false`, for the then-current `main` tree at commit `7d2980578fd6fa54da3acba5df42c844ed3d9538`.
- Each of the 46 individual file contents was fetched and its Git blob identity compared to the tree. **46/46 identities matched.**
- Targeted content checks searched for private-key headers, high-confidence cloud tokens, private host IPv4 login endpoints, internal absolute build paths, forced developer kernel boot settings and credential-like assignments. **No actual credential or private endpoint was identified in the 46 blobs.** One synthetic fixture deliberately assembled a fake credential string in a test; its source text was changed to avoid naïve scanner false alarms.
- The complete tree at the source-catalog PR was separately checked: **27/27 source/test/build files** matched registered Git blob identifiers, no missing paths and no truncated Git tree.
- GitHub's commits API was queried for the new repository's **41 then-reachable main commits**. Author/committer email domains observed were `users.noreply.github.com` and `github.com`, with no personal-address domain observed in that API result. This is not a report of any user's address.
- Main Git history is independent from private archival repository IDs; the historical old-repo source, keys, configs, firmware and experiment worktrees were not cloned into the new Git history.

## Blocking governance and execution gaps

- The GitHub rulesets API returned a **403 stating an upgraded plan or Public repository is required** for ruleset access on this Private repository. Main branch protection API also returned 403, citing integration access. **Therefore protected-main settings remain unverified and must not be represented as enforced.**
- GitHub-hosted workflow runs, including the source-catalog PR, have concluded FAILURE with job `steps=null`. This has not established source-code test failure, but it **does not establish any new CI PASS** either. Investigate hosted-runner entitlement/limits; avoid exposing a long-lived network-privileged home runner to public PR code just for a green badge.
- Current-tree inspection and sampled main commit metadata **do not replace the complete all-ref Git history scan**, PR/Issue text+comments, Actions artifacts/logs, unreachable Git objects, upstream contributor rights and vendor disclosure clearance.
- `rights_review` remains PENDING in every source-catalog entry. Matching hashes establish identity, **not a license grant**.

## Next source-publication gates

1. Run and archive the full strict source/history and workflow-policy checks on an isolated runner that can actually execute jobs.
2. Audit GitHub issue/PR descriptions, comments/reviews, and all Actions logs/assets; check reachable refs and retain proof of clean ancestry.
3. Resolve each source-catalog contributor-rights row with independently established attribution and any required upstream sign-off, without importing vendor SDK secrets.
4. Configure and read back repository security settings (main protection, minimal CI token rights, private vulnerability reporting) before visibility changes. If Private plan restrictions prevent settings, plan the controlled Public cutover and immediate protection, not a premature claim of existing enforcement.
5. Keep signer material, confidential research, unsafe prior firmware ZIP, radio personalization and complete OEM runtime out of this repo. Firmware-release criteria remain independently blocked.

This is a **limited but directly observed GitHub metadata and content review**, not an all-clear security certificate.
