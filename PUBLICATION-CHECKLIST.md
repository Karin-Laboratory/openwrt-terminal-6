# Publication gates / 公開判定

The project has eight guiding principles: **reproducibility**, **third-party rights**, **safety and recovery**, **honest validation status**, **traceability**, **community contribution**, **upstream cooperation**, and **maintainability**.

## Gate A: repository content (required for every PR)

- [ ] Every file is necessary, reviewed, and safe to publish.
- [ ] No credentials, signing material, unique device data, OEM images or unauthorized binaries are present in *any commit*.
- [ ] Third-party copyright notices, license terms and required source are recorded.
- [ ] No unsupported claims of successful hardware validation.
- [ ] Source origin and tests are recorded.

## Gate B: reproducible source release

- [ ] Pinned upstream source, dependency checksums and ordered patch series.
- [ ] Clean independent build with repeatable commands and full environment.
- [ ] Verified artifacts manifest, sizes, hashes and source correspondence.
- [ ] Per-component license compliance and redistribution approvals.
- [ ] CI builds from public inputs without private keys.

## Gate C: installable binary release (in addition to A + B)

- [ ] Exact revision/partition/slot preflight requirements verified.
- [ ] Restore/recovery path tested on appropriate hardware.
- [ ] Boot-chain acceptance and any signing constraints documented without exposing protected material.
- [ ] Relevant features and regressions independently tested.
- [ ] Installation guide includes explicit irreversible risks and stop conditions.
- [ ] Release notes record known limitations including 5G status.

**Gate status as of 2026-10-23:** Documentation/source research publication preparation only. Gate A requires complete history and per-file review and is **NOT YET SIGNED OFF**; Gates B and C **NOT PASSED**. See [RELEASE-READINESS.md](RELEASE-READINESS.md).

日本語: 「公開可能なソース」と「安全に導入可能なバイナリ」は別判定です。現在は文書のみを公開し、実機書込み可能な配布物は出しません。
