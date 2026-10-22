# Contributing / 参加方法

Contributions are welcome, especially clean-room build verification, board identification, tested kernel/OpenWrt patches and sanitized hardware logs.

1. Open an issue describing your hardware revision, component, and goal, without personal or secret identifiers.
2. Keep changes small and reviewable; cite upstream origin and licenses for imported code.
3. Include exact tool/OS versions, upstream commit, build commands, output hashes and sanitized logs.
4. Mark facts as **verified**, **reported**, **hypothesis**, or **not tested**. Never infer success from an absence of error messages.
5. For hardware-changing proposals, supply read-only diagnostics and risk analysis first; destructive writes require separate manual review.
6. Keep vendor artifacts and private signing materials out of git and GitHub Actions.
7. Submit PRs for review. Do not assume a PR implies endorsement for flashing hardware.

Priorities: (a) legal provenance, (b) exact hardware ID, (c) clean rebuild, (d) Ethernet/Wi-Fi validation, (e) 5G modem, (f) recovery tests, (g) upstreamable changes.

日本語: 改変差分、再現コマンド、検証ログ、ライセンス根拠を添えてください。未確認の事項は明示し、危険な書込み手順を未検証のまま公開しない方針です。
