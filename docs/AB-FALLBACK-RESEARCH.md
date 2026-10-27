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
