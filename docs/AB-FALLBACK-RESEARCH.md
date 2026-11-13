# A/B boot-control status: observed metadata versus fallback proof

**Development policy:** source-only offline simulation until reliable bootloader rescue has been independently verified. The new clean repository contains no bootloader image, signed boot payload, storage-write helper, key or device-specific metadata layout.

## What is known

Historical private research recorded a slot priority change and a readback with one slot's success flag asserted. The observed fields alone cannot answer **when the vendor LK decrements retry counters, how it chooses a fallback, whether it checks successful on every reboot, and how it handles a signature or kernel boot failure**.

## What was added

- [Read-only observation parser](../tools/boot/slot_observation.py) with strict allowed fields; deliberately never sets safe-to-switch.
- [Competing fallback hypotheses](../tools/boot/ab_fallback_hypotheses.py) supporting hypothetical ignore-counter, decrement-on-selection, and decrement-on-failure behavior. None is asserted to match vendor LK.
- [Synthetic regression tests](../tests/test_ab_fallback_hypotheses.py) exhibit that an unsuccessful, exhausted high-priority slot can still be chosen by a plausible implementation. This is an intentional counterexample to premature recovery claims.

## Evidence required before deployment is considered

1. Authorized, *read-only* observations from the device of interest and any independently available recovery console, with all identifiers and privileged network details retained privately.
2. Compare repeated **non-destructive** boot observations to theoretical state transitions; distinguish change made by userspace from the bootloader itself.
3. Identify independently verified recovery access *without relying solely on the slot being tested*.
4. Record which failure classes are covered: signed-header validation, kernel panic, userspace failure, watchdog and power loss are **not interchangeable**.
5. Confirm the hardware revision, rollback boundary and repeatability before creating any active A/B updater or release package.

A hypothetical simulator is not a device proof. No A/B mutation or flash command is supplied here.

## Relation to signature / firmware packaging

The bootloader's acceptance of a signed payload, the right to use the signing credentials, the content's integrity, and successful fallback are four independent conditions. None can substitute for the others. See [release gates](RELEASE-GATES.md).

## First-owner agent: S02/S03/S05 transition guard (2026-11-14)

The canonical stage IDs are S01 UART connection, S02 LK identification, S03 stock-B emergency shell identification, S04 stock SSH for the current boot, S05 persistence after reboot, S06 read-only P43/P44 inventory, S07 partition mutation or verified pre-existing P44, and S08 final acceptance. The entry JSON fetch is **preflight**, not an S01 PASS.

**S05 does not require permanently pinning slot B as the default boot slot.** Never auto-write retry/success/priority flags just to achieve SSH persistence. LK and U-Boot are not interchangeable interfaces. A bootloader help command, prompt character or earlier unit's log does not authorize any unknown boot command.

### Read-only evidence and decision checkpoints

| Observation point | Required evidence | Gate |
|---|---|---|
| Passive UART | Boot chronology, LK/OS identity and any observed slot hints | Logs stay private; if unclear use BLOCKED_IDENTITY |
| Identified LK | Version/context and demonstrably read-only capabilities, when available | Unknown LK command => do not send |
| Identified Linux shell | `uname -m`, `uname -r`, `cat /proc/cmdline`, `cat /proc/1/comm` | These are Linux-only, never send to LK |
| Authorized reboot | Next LK slot decision, stock-B Linux, external authenticated SSH with strict host key verification | A/B state change may consume retry counters; fresh owner approval required |

If the unit boots slot A and there is no validated stock-B recovery plan, report `BLOCKED_S03_BOOT_PATH`. If the unit already has authenticated stock-B SSH, inspect it non-destructively, but don't mark Emergency Shell S03 as passed without its own evidence. If a reboot returns another slot or drops SSH, keep S05/S08 blocked; distinguish possible watchdog/fallback/network/service causes without asserting one.

A read-only observer may verify current identity and report a planned transition. The exact next-boot choice, rollback, expected A/B metadata changes, and consequence of failure must be reviewed and specifically approved by the owner. No generic `fw_setenv`, blind misc sector writes, fixed GPT offsets or default credentials are supplied here.

See [firmware compatibility gate](TERMINAL6-FW-COMPATIBILITY.json). Historical kernel 5.4.238 is a research observation, **not** a validated compatibility profile. Unknown firmware, bootloader semantics or partition geometry blocks write paths. A completed S03 runbook and fresh-unit cold-boot validation remain outstanding.
