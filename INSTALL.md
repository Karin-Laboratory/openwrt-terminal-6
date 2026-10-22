# Installation / 導入

## STOP: no public flashing instructions yet

**Do not flash this project to a device based on the current repository.** Development reports do not establish a safe procedure for other hardware or board revisions.

Before any future installation guide is published, its reviewers must document:

- Exact commercial model and confirmed hardware/board identifiers; avoid guessing from research nicknames.
- The complete partition map and A/B boot behavior for the target revision.
- Read-only preflight checks, confirmed target slot and partition, and byte-for-byte backups with hashes.
- Whether boot-chain authentication permits the proposed image and which inputs are legally redistributable.
- A recovery path tested on comparable hardware, with serial access and power-loss behavior documented.
- Explicit written approval of any potentially destructive write step, never a wildcard device name or unverified partition number.

No `dd`, `fastboot flash`, vendor boot-control write command, or signed boot image is supplied here. A/B fallback **must not** be treated as proven or guaranteed.

日本語: **現段階では書込み禁止を推奨します。** 研究機で起動したという事実は、一般の機体で安全に導入できる証明ではありません。モデル・基板・スロット・対象パーティション・バックアップ・復旧経路を確認できる正式な導入手順が公開されるまで、機器への書込みを行わないでください。
