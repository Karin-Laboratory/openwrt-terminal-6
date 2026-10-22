#!/usr/bin/env python3
"""Validate factual board inventory without building or writing firmware."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def validate(data):
    issues = []
    if data.get("board_dts") != "NOT_YET_AVAILABLE":
        issues.append("DTS must remain unverified until reviewed")
    eth = data.get("ethernet", {})
    if eth.get("mac_node") != "mac@1" or eth.get("switch_cpu_port") != 5:
        issues.append("Ethernet mapping differs from Test24 evidence")
    if eth.get("test_link_mbps") != 100:
        issues.append("100Mbps test link cannot be claimed as a higher measured speed")
    wifi = data.get("wifi", {})
    if wifi.get("eeprom") != "PER_DEVICE_NOT_REDISTRIBUTED":
        issues.append("EEPROM must stay device-local")
    if 6 in wifi.get("confirmed_bands_ghz", []):
        issues.append("6 GHz client connection has not been verified")
    return issues

def main():
    board = json.loads((ROOT / "board/air-terminal-6.json").read_text())
    issues = validate(board)
    for issue in issues:
        print("FAIL:", issue)
    if issues:
        return 1
    print("PASS: developer-evidence board inventory (not bootable DTS)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
