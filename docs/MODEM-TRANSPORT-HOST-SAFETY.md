# MT6990 modem transport host-only timeout and correlation model (2026-10-30)

This project does **not** yet provide a rights-cleared CCCI/MIPC/RIL transport, driver or live modem cancellation mechanism. The standalone Python state model exists to test safe *local* request correlation assumptions in Issue #22.

## New negative behavior

- Local request IDs are strictly increasing inside each generation, including after a completion or local deadline expiration. This prevents a delayed response for an old request from being misinterpreted as a newly reused ID with the same length.
- `expire_local(generation, id)` discards only a local pending slot; it does **not** send a modem abort, cancel a relay or prove that an asynchronous hardware transaction finished. A late reply is rejected by `complete` after local expiry.
- Wrong-generation operations are rejected. `stop()` invalidates the generation; a subsequent independent `begin()` resets correlation state.
- Request IDs and length must be actual integers (not booleans); payload and queue bounds remain enforced.
- The four `data_ready()` evidence flags must be explicit `True` booleans; truthy strings, integers or arbitrary objects cannot promote a synthetic session to `DATA_READY`. This is a host-model invariant, **not** a real LTE/NR dataplane test.
- Response correlation now rejects non-integer generation, request ID and payload length fields, including Python booleans and integer-equivalent floats. Invalid response fields return `False` without consuming the pending request; invalid generation is a state-transition error. These are host-only negative tests, not validation of a real CCCI/MIPC wire decoder.

## Limitations and follow-up

This host-only model has no real deadline clock, no wire format, interrupt, CCCI buffer, RF/network interface or cancellation ACK. It cannot verify modem readiness, LTE/NR search completion, PDN success or packet transfer. In particular, **do not rerun asynchronous NR/PLMN scanning merely because the local wait expired**. Only an independently confirmed modem-transport cancellation/completion protocol can authorize safe retries.

Next #22 gates: audit and attribute actual CCCI/MIPC/RIL dependencies; implement an independent rights-cleared transport with bounded lifecycle and explicit remote completion/cancellation semantics; run host tests, compile with a matching kernel and only then undertake separately approved real-device testing. Historical Stage10 LTE IPv4 remains distinct from Public reproduction.
