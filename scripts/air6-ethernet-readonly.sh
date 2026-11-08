#!/bin/sh
# SPDX-License-Identifier: MIT
# Observation only: never alter routes, VLANs, PHY state, flash, slots or NICs.
set -eu
printf '%s\n' 'AIR6_RX_READONLY_BEGIN'
printf '%s\n' '=== LINKS ==='
ip -s link show dev eth1 || :
printf '%s\n' '=== CARRIER ==='
cat /sys/class/net/eth1/carrier 2>/dev/null || :
printf '%s\n' '=== PCS/DRIVER COUNTERS ==='
ethtool -S eth1 2>/dev/null || :
printf '%s\n' '=== VLAN/DSA ==='
bridge vlan show 2>/dev/null || :
printf '%s\n' '=== NEIGH ==='
ip neigh show dev eth1 || :
printf '%s\n' 'AIR6_RX_READONLY_END'
