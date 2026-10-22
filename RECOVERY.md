# Recovery / 復旧

**Status: recovery from third-party installation is NOT VERIFIED.**

Do not assume that the bootloader automatically returns to the previous slot, that retry counters decrement predictably, or that a UART prompt is always accessible.

A future recovery document must identify:

1. Hardware revision and exact state before failure.
2. Non-destructive diagnosis via UART and read-only partition/boot-control inspection.
3. Checksummed backups acquired *before* any modification.
4. Verified entry into a known-good boot path.
5. Controlled restoration using an independently validated image, approved partition target, power stability and readback comparison.
6. Expected logs, stop conditions, rollback criteria and tests after recovery.

Do not publish untested write recipes or private OEM binaries/keys. If a unit does not match documented assumptions, **stop** rather than improvising recovery.

日本語: 第三者機体の復旧方法は未検証です。A/B自動復帰を前提にしないでください。読み取り専用調査・事前バックアップ・条件が一致する復旧手順の実機検証を終えてから手順を公開します。
