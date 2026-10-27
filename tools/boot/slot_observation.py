# SPDX-License-Identifier: MIT
"""Read-only A/B metadata observation model. No device I/O or write operations.

Bootability, LK decrement rules and fallback CANNOT be inferred from these
fields alone; never use this module to authorize a slot switch or flash.
"""
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SlotObservation:
    label: str
    priority: int
    tries_remaining: int
    successful: bool

    def __post_init__(self):
        if self.label not in ("A", "B"):
            raise ValueError("invalid generic slot label")
        for name, value, maximum in (
            ("priority", self.priority, 15),
            ("tries_remaining", self.tries_remaining, 7),
        ):
            if type(value) is not int or not 0 <= value <= maximum:
                raise ValueError("invalid " + name)
        if type(self.successful) is not bool:
            raise ValueError("successful must be a boolean")


def from_sanitized_fields(values: Mapping[str, object]) -> SlotObservation:
    """Reject unexpected fields to avoid importing raw device identifiers."""
    required = {"label", "priority", "tries_remaining", "successful"}
    if set(values) != required:
        raise ValueError("unexpected or missing observation fields")
    return SlotObservation(
        label=values["label"],
        priority=values["priority"],
        tries_remaining=values["tries_remaining"],
        successful=values["successful"],
    )


def summarize(a: SlotObservation, b: SlotObservation) -> dict:
    """Report only metadata facts, never prediction or deployment approval."""
    if (a.label, b.label) != ("A", "B"):
        raise ValueError("exactly A then B required")
    if a.priority == b.priority:
        order = "equal priority fields"
    else:
        order = "A higher priority field" if a.priority > b.priority else "B higher priority field"
    return {
        "priority_field_order": order,
        "successful_flags": [s.label for s in (a, b) if s.successful],
        "fallback_proven": False,
        "safe_to_switch": False,
        "reason": (
            "Metadata flags do not establish LK retry decrement timing, "
            "fallback threshold, verified firmware contents or independent rescue"
        ),
    }
