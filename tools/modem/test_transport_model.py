# SPDX-License-Identifier: MIT
import unittest
from transport_model import ModemState, Phase, TransitionError


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.m = ModemState()
        self.g = self.m.begin()

    def ready(self):
        self.m.transport_ready(self.g)
        self.m.control_ready(self.g)
        self.m.registered(self.g)

    def test_complete_requires_dataplane_evidence(self):
        self.ready()
        with self.assertRaises(TransitionError):
            self.m.data_ready(self.g, interface_up=True, address=True,
                              route=True, bidirectional=False)
        self.assertEqual(self.m.phase, Phase.REGISTERED)
        self.m.data_ready(self.g, interface_up=True, address=True,
                          route=True, bidirectional=True)
        self.assertEqual(self.m.phase, Phase.DATA_READY)

    def test_ccci_ready_not_data_ready(self):
        self.m.transport_ready(self.g)
        self.assertNotEqual(self.m.phase, Phase.DATA_READY)
        with self.assertRaises(TransitionError):
            self.m.registered(self.g)

    def test_bounded_lengths_and_queue(self):
        self.m.transport_ready(self.g)
        for size in (-1, 65537):
            with self.assertRaises(TransitionError):
                self.m.send(self.g, 1, size)
        for index in range(1, 33):
            self.m.send(self.g, index, 0)
        with self.assertRaises(TransitionError):
            self.m.send(self.g, 33, 0)
        self.assertFalse(self.m.complete(self.g, 1, 1))
        self.assertTrue(self.m.complete(self.g, 1, 0))

    def test_stale_completion_rejected_after_stop(self):
        self.m.transport_ready(self.g)
        self.m.send(self.g, 10, 3)
        self.m.stop()
        with self.assertRaises(TransitionError):
            self.m.complete(self.g, 10, 3)
        self.assertEqual(self.m.pending, {})

    def test_failure_and_restart_invalidate_generation(self):
        self.m.transport_ready(self.g)
        self.m.fail(self.g, "synthetic timeout")
        self.assertEqual(self.m.phase, Phase.FAILED)
        new = self.m.begin()
        self.assertNotEqual(new, self.g)
        with self.assertRaises(TransitionError):
            self.m.transport_ready(self.g)
        self.m.transport_ready(new)
        self.assertEqual(self.m.phase, Phase.TRANSPORT_READY)

    def test_invalid_and_duplicate_requests(self):
        self.m.transport_ready(self.g)
        with self.assertRaises(TransitionError):
            self.m.send(self.g, 0, 0)
        self.m.send(self.g, 1, 2)
        with self.assertRaises(TransitionError):
            self.m.send(self.g, 1, 2)

    def test_expired_local_request_cannot_accept_late_reply(self):
        self.m.transport_ready(self.g)
        self.m.send(self.g, 8, 0)
        self.assertTrue(self.m.expire_local(self.g, 8))
        self.assertFalse(self.m.expire_local(self.g, 8))
        self.assertFalse(self.m.complete(self.g, 8, 0))
        with self.assertRaises(TransitionError):
            self.m.send(self.g, 8, 0)
        self.m.send(self.g, 9, 0)
        self.assertTrue(self.m.complete(self.g, 9, 0))

    def test_monotonic_ids_after_completion_and_zero_length(self):
        self.m.transport_ready(self.g)
        self.m.send(self.g, 21, 0)
        self.assertTrue(self.m.complete(self.g, 21, 0))
        with self.assertRaises(TransitionError):
            self.m.send(self.g, 21, 0)
        with self.assertRaises(TransitionError):
            self.m.send(self.g, 20, 0)
        self.m.send(self.g, 22, 0)

    def test_old_generation_cannot_expire_new_session(self):
        self.m.transport_ready(self.g)
        self.m.send(self.g, 10, 2)
        self.m.stop()
        new_gen = self.m.begin()
        self.m.transport_ready(new_gen)
        self.m.send(new_gen, 10, 2)
        with self.assertRaises(TransitionError):
            self.m.expire_local(self.g, 10)
        self.assertTrue(self.m.complete(new_gen, 10, 2))

    def test_bool_length_and_id_not_accepted(self):
        self.m.transport_ready(self.g)
        with self.assertRaises(TransitionError):
            self.m.send(self.g, True, 0)
        with self.assertRaises(TransitionError):
            self.m.send(self.g, 1, False)
        self.assertEqual(self.m.last_request_id, 0)


if __name__ == "__main__":
    unittest.main()
