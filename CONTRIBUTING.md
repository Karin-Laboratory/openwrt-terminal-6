# Contributing

Thank you for taking an interest in OpenWrt research for the SoftBank Air Terminal 6. Source review, reproducible host-only tests, documentation corrections and small upstream-oriented patches are welcome. You do **not** need to own the hardware to contribute.

## Good first contributions

- Check documentation links, terminology and independently reproducible claims.
- Run or improve the offline, hardware-free tests under `tests/`.
- Review Linux/Device Tree patch structure, binding requirements and license attribution.
- Report a well-scoped source bug or propose a small patch, with a minimal test or an explanation of how you checked it.

Before filing an Issue, consult [technical status](docs/STATUS.md), [roadmap](docs/ROADMAP.md), [build contract](docs/BUILD-CONTRACT.md) and existing Issues. For new work, state what you observed, the source revision or file path, what you expected, and how someone without a device could reproduce it. Separate your observations from hypotheses.

## Pull request checklist

1. Keep one logically reviewable change per PR and explain its purpose.
2. Include the origin, applicable license and copyright attribution for new source material.
3. Identify test commands actually executed and results; do not claim a device test from a synthetic test.
4. Avoid introducing new firmware downloads, build side effects, trusted-runner dependencies or flashing steps.
5. Keep GPL kernel derivatives under appropriate GPL terms, and never invent contributor `Signed-off-by` lines.

## Security, privacy and device safety

Never post proprietary SDK code, vendor binaries, confidential logs, unique device identifiers, passwords, SIM/subscriber data, radio calibration, signing material, network access details or actionable unpublished vulnerability information. Please see [SECURITY.md](SECURITY.md) for confidential reports rather than creating a public Issue.

This is a **source-only research repository**. It does not offer an installable firmware or verified recovery process. Experimental device changes and firmware packaging are outside its public contribution path. External pull requests must not execute on network-privileged self-hosted machines.

This project is independent of SoftBank and is not an official OpenWrt release.
