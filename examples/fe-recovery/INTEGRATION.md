# FE recovery reference: Linux workqueue integration contract

This is a design contract for the standalone C state machine in this directory, **not** a ready-to-apply Linux kernel patch. No hardware or vendor code is needed.

## Required concurrency boundaries

A future kernel adapter must serialize every call to `t6_fe_request`, `t6_fe_take_pending`, `t6_fe_failure`, `t6_fe_success`, and `t6_fe_stop` against **the same state lock**. Current reference functions perform no locking themselves. They must never be called concurrently without that adapter.

- **Producer:** acquire the lock, reject requests after shutdown, record pending bits, and decide if a work item needs scheduling. Preserve a pending request even when `schedule_work()` reports that the worker is already queued.
- **Worker:** take and clear pending bits under the lock, release it before doing any hardware or modem-side work. Work execution must check the driver's lifetime and resource ownership again before touching registers.
- **Retry:** a non-zero delay from `t6_fe_failure` is just the model's backoff suggestion. The adapter must define when and under which lock it arms `mod_delayed_work()`, and must not rearm after shutdown. Modem-ownership busy retries are a separate policy.
- **Completion:** mark recovery successful only when *both* FE and modem-side recovery conditions are satisfied. A stale retry callback must not erase a newer request.
- **Teardown:** set shutdown with the same lock, then release it before calling synchronous work cancellation (which may wait for a callback needing that lock). Quiesce before DMA unmap, unregister, netdev teardown or resource release. Probe error paths require the same ordering once work has been initialized.

## Important gaps in the reference C model

The model tracks five suggested delays (5, 10, 20, 40, 40 seconds). It records `exhausted` only on the *next* failed-recovery accounting call; the adapter must clearly define that event and the meaning of the final scheduled retry. It has no time source, lifecycle generation counter, atomicity, DMA logic, spinlocks or real workqueue objects. Those omissions are intentional and need implementation and stress testing.

Do not call this model a complete `mtk_eth_soc.c` modification. The actual Test34 source and its derivative licensing need review separately.

## Release gates

A future Linux integration requires: a public pinned upstream tree, patch series with provenance, MT6990 and unaffected-SoC compilation, KUnit or other state tests, lockdep/KASAN stress on teardown versus callbacks, simulated modem ownership, and independently reviewed device recovery. Until then it remains a safe, host-testable reference.
