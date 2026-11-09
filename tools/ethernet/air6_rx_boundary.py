#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline MT7531 CPU5 / MT6990 MAC1 receive-boundary classification.

Inputs are explicit owner-supplied READ-ONLY counter snapshots, not private
register dumps or credentials. Link UP alone can never count as packet PASS.
"""
import argparse
import json
from pathlib import Path

COUNTERS = ("switch_port1_rx_broadcast", "switch_cpu5_tx_broadcast",
            "switch_cpu5_rx", "mac1_rx", "eth1_rx", "eth1_tx",
            "arp_replies", "icmp_echo_replies")


def delta(before, after):
    if set(before) != set(COUNTERS) or set(after) != set(COUNTERS):
        raise ValueError("RX_COUNTER_SCHEMA")
    result = {}
    for key in COUNTERS:
        a, b = before[key], after[key]
        if type(a) is not int or type(b) is not int or a < 0 or b < a:
            raise ValueError("RX_COUNTER_RESET_OR_WRAP_" + key)
        result[key] = b - a
    return result


def analyze(before, after, metadata):
    if not isinstance(metadata, dict):
        raise ValueError("RX_METADATA")
    if metadata.get("link_mode") != "2500base-x" or metadata.get("uplink") != "MAC1-PCS1-SGMII1-MT7531-CPU5":
        raise ValueError("RX_TOPOLOGY_NOT_VERIFIED")
    d = delta(before, after)
    progressed = d["switch_port1_rx_broadcast"] > 0 and d["switch_cpu5_tx_broadcast"] > 0
    if not progressed:
        status = "NO_PACKET_PATH_EVIDENCE"
    elif not (d["mac1_rx"] or d["eth1_rx"]) and not d["switch_cpu5_rx"]:
        status = "CPU5_TO_MAC1_RX_BOUNDARY_SUSPECT"
    elif not d["arp_replies"]:
        status = "MAC_TRAFFIC_SEEN_ARP_UNRESOLVED"
    elif not d["icmp_echo_replies"]:
        status = "ARP_SEEN_ICMP_UNPROVEN"
    elif d["mac1_rx"] and d["eth1_rx"] and d["eth1_tx"]:
        status = "OFFLINE_COUNTER_PATH_CONSISTENT_NOT_HARDWARE_PROOF"
    else:
        status = "INCOMPLETE_RECEIVE_PATH"
    # VLAN/DSA/copper/PCS electrical state cannot be inferred from counters.
    return {"classification": status, "delta": d, "link_only_pass": False,
            "vlan_dsa_parser_proven": False, "real_hardware_pass": False,
            "needs": ["actual DSA tag", "VLAN table", "CPU5 PCS/electrical state",
                      "two-way ARP/ICMP on the target device"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--before", required=True, type=Path)
    ap.add_argument("--after", required=True, type=Path)
    ap.add_argument("--topology", required=True, type=Path)
    args = ap.parse_args()
    out = analyze(json.loads(args.before.read_text()), json.loads(args.after.read_text()),
                  json.loads(args.topology.read_text()))
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
