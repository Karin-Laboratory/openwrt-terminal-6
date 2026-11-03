# Contributing

Thank you for taking an interest in OpenWrt for the SoftBank Air Terminal 6. Proven backports, independent observation-based drivers/DTS, reproducible unsigned p25/p26 builds, tests, source review and documentation are welcome. See the [active mainline policy](docs/MAINLINE-P25-P26-POLICY.md). You do **not** need to own the hardware to contribute.

## Good first contributions

- Check documentation links, terminology and independently reproducible claims.
- Run offline tests or advance ephemeral unsigned p25/p26 build integration.
- Review Linux/Device Tree patch structure, binding requirements and license attribution.
- Report a well-scoped source bug or propose a small patch, with a minimal test or an explanation of how you checked it.

Before filing an Issue, consult [technical status](docs/STATUS.md), [roadmap](docs/ROADMAP.md), [build contract](docs/BUILD-CONTRACT.md) and existing Issues. For new work, state what you observed, the source revision or file path, what you expected, and how someone without a device could reproduce it. Separate your observations from hypotheses.

## Pull request checklist

1. Keep one logically reviewable change per PR and explain its purpose.
2. Include **one origin line** for added/backported code: upstream URL + revision or independent observation/self-authorship, SPDX/license and unresolved third-party concerns. Do not treat AI assistance alone as proof of authorship or permission.
3. Identify test commands actually executed and results; do not claim a device test from a synthetic test.
4. Ephemeral unsigned CI builds are welcome. Do not introduce public binary uploads (Actions artifacts, Releases, caches, registries), trusted-runner dependencies or device flashing. A public PR already publishes its source.
5. Keep GPL kernel derivatives under appropriate GPL terms, and never invent contributor `Signed-off-by` lines.

## Security, privacy and device safety

Never post proprietary SDK code, vendor binaries, confidential logs, unique device identifiers, passwords, SIM/subscriber data, radio calibration, signing material, network access details or actionable unpublished vulnerability information. Please see [SECURITY.md](SECURITY.md) for confidential reports rather than creating a public Issue.

**Public distribution is presently source-only**, but building and packaging unsigned p25/p26 for isolated verification is the current development goal. Distributing installable firmware, signing, bypass instructions and device flashing are separate decisions. External pull requests must not execute on network-privileged self-hosted machines.

This project is independent of SoftBank and is not an official OpenWrt release.
