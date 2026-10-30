# SPDX-License-Identifier: MIT
"""Hardware-free lifecycle model for an eventual MT6990 modem transport.

Not a CCCI or MIPC wire implementation; no vendor framing is assumed.
"""
from dataclasses import dataclass, field
from enum import Enum, auto


class Phase(Enum):
    OFF = auto()
    INITIALIZING = auto()
    TRANSPORT_READY = auto()
    CONTROL_READY = auto()
    REGISTERED = auto()
    DATA_READY = auto()
    FAILED = auto()


class TransitionError(ValueError):
    pass


@dataclass
class ModemState:
    phase: Phase = Phase.OFF
    generation: int = 0
    pending: dict[int, int] = field(default_factory=dict)
    last_request_id: int = 0  # Per-generation monotonic ID: reject late response aliasing.
    max_payload: int = 65536
    max_pending: int = 32
    last_error: str = ""

    def begin(self) -> int:
        if self.phase not in (Phase.OFF, Phase.FAILED):
            raise TransitionError("already active")
        self.generation += 1
        self.pending.clear()
        self.last_request_id = 0
        self.last_error = ""
        self.phase = Phase.INITIALIZING
        return self.generation

    def transport_ready(self, generation: int) -> None:
        self._require(generation, Phase.INITIALIZING)
        self.phase = Phase.TRANSPORT_READY

    def control_ready(self, generation: int) -> None:
        self._require(generation, Phase.TRANSPORT_READY)
        self.phase = Phase.CONTROL_READY

    def registered(self, generation: int) -> None:
        self._require(generation, Phase.CONTROL_READY)
        self.phase = Phase.REGISTERED

    def data_ready(self, generation: int, *, interface_up: bool, address: bool,
                   route: bool, bidirectional: bool) -> None:
        self._require(generation, Phase.REGISTERED)
        # Truthy integers/strings/objects are not independent dataplane evidence.
        # Require explicit booleans for each of the four host-only checks.
        if not all(type(flag) is bool and flag for flag in
                   (interface_up, address, route, bidirectional)):
            raise TransitionError("data plane unverified")
        self.phase = Phase.DATA_READY

    def send(self, generation: int, request_id: int, size: int) -> None:
        if self.phase not in (Phase.TRANSPORT_READY, Phase.CONTROL_READY,
                              Phase.REGISTERED, Phase.DATA_READY):
            raise TransitionError("transport not ready")
        self._current(generation)
        if type(request_id) is not int or not (0 < request_id <= 0xFFFFFFFF):
            raise TransitionError("invalid local request id")
        if type(size) is not int or not (0 <= size <= self.max_payload):
            raise TransitionError("payload length out of bounds")
        if request_id <= self.last_request_id:
            raise TransitionError("request ids must increase within one generation")
        if len(self.pending) >= self.max_pending:
            raise TransitionError("request queue full")
        self.pending[request_id] = size
        self.last_request_id = request_id

    def complete(self, generation: int, request_id: int, size: int) -> bool:
        self._current(generation)
        # Python bool and float compare equal to integers (True == 1, 1.0 == 1).
        # Untrusted response fields must not alias an outstanding request.
        if (type(request_id) is not int or type(size) is not int
                or not (0 < request_id <= 0xFFFFFFFF)
                or not (0 <= size <= self.max_payload)):
            return False
        expected = self.pending.get(request_id)
        if expected is None or expected != size:
            return False
        del self.pending[request_id]
        return True

    def expire_local(self, generation: int, request_id: int) -> bool:
        """Discard local pending correlation after a deadline.

        This DOES NOT cancel an asynchronous request inside the modem, relay or
        kernel transport. Its late reply is ignored. Do not reuse the request
        ID within this generation; start a newly verified generation instead.
        """
        self._current(generation)
        if type(request_id) is not int or not (0 < request_id <= 0xFFFFFFFF):
            raise TransitionError("invalid local request id")
        return self.pending.pop(request_id, None) is not None

    def fail(self, generation: int, error: str) -> None:
        self._current(generation)
        self.pending.clear()
        self.last_error = error[:120]
        self.phase = Phase.FAILED

    def stop(self) -> None:
        self.generation += 1
        self.pending.clear()
        self.phase = Phase.OFF
        self.last_error = ""

    def _current(self, generation: int) -> None:
        # Avoid True == 1 and 1.0 == 1 bypassing generation correlation.
        if (type(generation) is not int or generation <= 0
                or generation != self.generation):
            raise TransitionError("stale or invalid generation")

    def _require(self, generation: int, phase: Phase) -> None:
        self._current(generation)
        if self.phase is not phase:
            raise TransitionError(f"expected {phase.name}, got {self.phase.name}")
