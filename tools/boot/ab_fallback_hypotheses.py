# SPDX-License-Identifier: MIT
"""Pure A/B boot fallback hypothesis simulator with NO device access.

The policies here are deliberate competing assumptions, NOT LK behavior.
Never use a simulator result as authorization to switch, erase or flash a slot.
"""
from dataclasses import dataclass, replace
from enum import Enum


@dataclass(frozen=True)
class Slot:
    label: str
    priority: int
    retries: int
    successful: bool
    image_accepted: bool

    def __post_init__(self):
        if self.label not in ("A", "B"):
            raise ValueError("unknown slot")
        if type(self.priority) is not int or not 0 <= self.priority <= 15:
            raise ValueError("invalid priority")
        if type(self.retries) is not int or not 0 <= self.retries <= 7:
            raise ValueError("invalid retries")
        if type(self.successful) is not bool or type(self.image_accepted) is not bool:
            raise ValueError("invalid status type")


class RetryPolicy(Enum):
    IGNORE_COUNTER = "ignore_counter"
    DECREMENT_ON_SELECTION = "decrement_on_selection"
    DECREMENT_ON_FAILURE = "decrement_on_failure"


def step(a: Slot, b: Slot, policy: RetryPolicy):
    """Hypothetical single boot attempt. Read-only, returns new immutable slots.

    Choice is based on priority field alone. This is not an assertion about LK.
    A failed slot may keep priority after retries are exhausted: no safe
    automatic failover is assumed or fabricated.
    """
    if (a.label, b.label) != ("A", "B") or not isinstance(policy, RetryPolicy):
        raise ValueError("invalid input")
    target = a if a.priority >= b.priority else b
    chosen = target.label
    if target.priority == 0:
        return a, b, None, False
    if policy is RetryPolicy.DECREMENT_ON_SELECTION and not target.successful:
        target = replace(target, retries=max(target.retries - 1, 0))
    accepted = target.image_accepted
    if (policy is RetryPolicy.DECREMENT_ON_FAILURE and
            not accepted and not target.successful):
        target = replace(target, retries=max(target.retries - 1, 0))
    if chosen == "A":
        a = target
    else:
        b = target
    return a, b, chosen, accepted


def compare_policies(a: Slot, b: Slot, cycles: int = 4) -> dict:
    """Show divergent outcomes, never a prediction or validated fallback."""
    if not 1 <= cycles <= 20 or (a.label, b.label) != ("A", "B"):
        raise ValueError("invalid simulation bounds")
    outcomes = {}
    for policy in RetryPolicy:
        x, y = a, b
        trace = []
        for _ in range(cycles):
            x, y, label, accepted = step(x, y, policy)
            trace.append({"selected": label, "accepted": accepted,
                          "retries": (x.retries, y.retries)})
        outcomes[policy.value] = trace
    return {
        "assumption": "unverified theoretical models, not vendor LK specification",
        "fallback_proven": False,
        "safe_to_modify_device": False,
        "traces": outcomes,
    }
