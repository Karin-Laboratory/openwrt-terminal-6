# SPDX-License-Identifier: MIT
import unittest
from tools.ethernet import air6_rx_boundary as rx


def sample():
    return dict.fromkeys(rx.COUNTERS, 0)


class RXBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.before = sample()
        self.after = sample()
        self.topology = dict(link_mode="2500base-x",
                             uplink="MAC1-PCS1-SGMII1-MT7531-CPU5")

    def test_rc14_observed_boundary_not_link_pass(self):
        self.after["switch_port1_rx_broadcast"] = 3
        self.after["switch_cpu5_tx_broadcast"] = 3
        result = rx.analyze(self.before, self.after, self.topology)
        self.assertEqual(result["classification"], "CPU5_TO_MAC1_RX_BOUNDARY_SUSPECT")
        self.assertFalse(result["real_hardware_pass"])

    def test_arp_resolution_and_icmp_are_distinct(self):
        self.after.update(switch_port1_rx_broadcast=2, switch_cpu5_tx_broadcast=2,
                          mac1_rx=2, eth1_rx=2)
        self.assertEqual(rx.analyze(self.before, self.after, self.topology)["classification"],
                         "MAC_TRAFFIC_SEEN_ARP_UNRESOLVED")
        self.after["arp_replies"] = 1
        self.assertEqual(rx.analyze(self.before, self.after, self.topology)["classification"],
                         "ARP_SEEN_ICMP_UNPROVEN")

    def test_successful_counters_still_not_real_air6_proof(self):
        self.after.update({key: 2 for key in rx.COUNTERS})
        result = rx.analyze(self.before, self.after, self.topology)
        self.assertIn("CONSISTENT", result["classification"])
        self.assertFalse(result["real_hardware_pass"])

    def test_missing_or_reset_counter_rejected(self):
        self.after.pop("mac1_rx")
        with self.assertRaisesRegex(ValueError, "RX_COUNTER_SCHEMA"):
            rx.analyze(self.before, self.after, self.topology)
        self.after = sample()
        self.before["mac1_rx"] = 4
        with self.assertRaisesRegex(ValueError, "RESET_OR_WRAP"):
            rx.analyze(self.before, self.after, self.topology)

    def test_topology_mismatch_rejected(self):
        self.topology["link_mode"] = "sgmii"
        with self.assertRaisesRegex(ValueError, "RX_TOPOLOGY"):
            rx.analyze(self.before, self.after, self.topology)


if __name__ == "__main__":
    unittest.main()
