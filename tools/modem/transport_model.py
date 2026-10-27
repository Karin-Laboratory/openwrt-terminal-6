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
    max_payload: int = 65536
    max_pending: int = 32
    last_error: str = ""

    def begin(self) -> int:
        if self.phase not in (Phase.OFF, Phase.FAILED):
            raise TransitionError("already active")
        self.generation += 1
        self.pending.clear()
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
        if not all((interface_up, address, route, bidirectional)):
            raise TransitionError("data plane unverified")
        self.phase = Phase.DATA_READY

    def send(self, generation: int, request_id: int, size: int) -> None:
        if self.phase not in (Phase.TRANSPORT_READY, Phase.CONTROL_READY,
                              Phase.REGISTERED, Phase.DATA_READY):
            raise TransitionError("transport not ready")
        self._current(generation)
        if not (0 < request_id <= 0xFFFFFFFF):
            raise TransitionError("invalid local request id")
        if not (0 <= size <= self.max_payload):
            raise TransitionError("payload length out of bounds")
        if request_id in self.pending or len(self.pending) >= self.max_pending:
            raise TransitionError("duplicate request or queue full")
        self.pending[request_id] = size

    def complete(self, generation: int, request_id: int, size: int) -> bool:
        self._current(generation)
        expected = self.pending.get(request_id)
        if expected is None or expected != size:
            return False
        del self.pending[request_id]
        return True

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
        if generation != self.generation:
            raise TransitionError("stale generation")

    def _require(self, generation: int, phase: Phase) -> None:
        self._current(generation)
        if self.phase is not phase:
            raise TransitionError(f"expected {phase.name}, got {self.phase.name}")
