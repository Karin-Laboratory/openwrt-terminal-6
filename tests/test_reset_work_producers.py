import unittest

from tools.check_mediatek_rfc_series import unguarded_pending_work_lines


class ResetWorkProducerTests(unittest.TestCase):
    def test_queue_inside_serialized_helper_is_allowed(self):
        source = """static void __mtk_queue_reset_work(struct mtk_eth *eth)
{
	if (!eth->reset_queue_stopping)
		schedule_work(&eth->pending_work);
}
static void mtk_queue_reset_work(struct mtk_eth *eth) { }
"""
        self.assertEqual(unguarded_pending_work_lines(source), [])

    def test_downstream_direct_producer_is_reported(self):
        source = """static void __mtk_queue_reset_work(struct mtk_eth *eth)
{
	schedule_work(&eth->pending_work);
}
static void mtk_queue_reset_work(struct mtk_eth *eth) { }
static void mtk_mac_finish(struct mtk_eth *eth)
{
	schedule_work(&eth->pending_work);
}
"""
        self.assertEqual(unguarded_pending_work_lines(source), [8])

    def test_missing_helper_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "helper boundary"):
            unguarded_pending_work_lines("schedule_work(&eth->pending_work);")


if __name__ == "__main__":
    unittest.main()
