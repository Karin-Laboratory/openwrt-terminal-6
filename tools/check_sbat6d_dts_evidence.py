#!/usr/bin/env python3
"""Assess readiness to author an independent SBAT6D DTS from public evidence.

No DTS is generated. Never infer missing providers, phandles or board IDs.
"""
import argparse
import json
from pathlib import Path
import sys

REQUIRED = (
    "board_identity",
    "runtime_fdt_provenance",
    "complete_node_inventory",
    "ethernet_mac_switch_wiring",
    "clock_providers_and_ids",
    "power_domain_providers_and_ids",
    "sgmii_pll_and_phy_binding",
    "pinmux_resets_regulators",
    "kernel_binding_validation",
)

def audit(document):
    checks = document.get("checks", {})
    approved = []
    blockers = []
    for name in REQUIRED:
        item = checks.get(name)
        evidence = item.get("evidence") if isinstance(item, dict) else None
        # A simple placeholder string is not proof. Require a traceable source,
        # recorded hash, and a reviewer statement for each technical claim.
        supported = (isinstance(evidence, dict)
                     and isinstance(evidence.get("source"), str)
                     and evidence["source"].strip()
                     and isinstance(evidence.get("sha256"), str)
                     and len(evidence["sha256"]) == 64
                     and all(ch in "0123456789abcdef" for ch in evidence["sha256"])
                     and evidence.get("reviewed") is True)
        if not isinstance(item, dict) or item.get("status") != "verified" or not supported:
            blockers.append(name)
        else:
            approved.append(name)
    return {
        "schema": "sbat6d-dts-gate-v1",
        "scope": "source readiness only; not a hardware boot authorization",
        "ready_for_board_dts_review": not blockers,
        "verified": approved,
        "blocked": blockers,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = audit(json.loads(args.inventory.read_text()))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if args.require_complete and result["blocked"] else 0

if __name__ == "__main__":
    sys.exit(main())
