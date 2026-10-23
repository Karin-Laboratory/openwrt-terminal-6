#!/usr/bin/env python3
"""Check lifecycle invariants in a v6.18 tree after applying RFC 0001/0002."""
import argparse
from pathlib import Path
import sys


def body(source: str, start: str, end: str) -> str:
    try:
        return source.split(start, 1)[1].split(end, 1)[0]
    except IndexError as exc:
        raise ValueError(f"function boundary not found: {start}") from exc


def check(root: Path) -> None:
    c = (root / "drivers/net/ethernet/mediatek/mtk_eth_soc.c").read_text()
    h = (root / "drivers/net/ethernet/mediatek/mtk_eth_soc.h").read_text()

    queue_inner = body(c, "static void __mtk_queue_reset_work(", "static void mtk_queue_reset_work(")
    queue = body(c, "static void mtk_queue_reset_work(", "static void mtk_stop_reset_work(")
    stop = body(c, "static void mtk_stop_reset_work(", "static void mtk_tx_timeout(")
    tx = body(c, "static void mtk_tx_timeout(", "static int mtk_get_irqs(")
    monitor = body(c, "static void mtk_hw_reset_monitor_work(", "static int mtk_hw_init(")
    probe = body(c, "static int mtk_probe(", "static void mtk_remove(")
    remove = body(c, "static void mtk_remove(", "static const struct mtk_soc_data mt2701_data")

    if "if (!eth->reset_queue_stopping)" not in queue_inner:
        raise ValueError("pending_work producer does not test stop latch")
    if "schedule_work(&eth->pending_work)" not in queue_inner:
        raise ValueError("guarded helper does not queue pending_work")
    if "spin_lock_irqsave(&eth->reset_queue_lock, flags)" not in queue or "__mtk_queue_reset_work(eth);" not in queue:
        raise ValueError("monitor reset work producer is not protected by reset_queue_lock")
    if "schedule_work(&eth->pending_work)" in tx or "schedule_work(&eth->pending_work)" in monitor:
        raise ValueError("an unguarded pending_work producer remains")
    if not all(part in tx for part in (
        "spin_lock_irqsave(&eth->reset_queue_lock, flags)",
        "eth->reset_queue_stopping || test_bit(MTK_RESETTING, &eth->state)",
        "!mtk_hw_reset_check(eth)",
        "__mtk_queue_reset_work(eth);",
        "spin_unlock_irqrestore(&eth->reset_queue_lock, flags)",
    )):
        raise ValueError("tx_timeout check and producer are not serialized with teardown")
    tx_lock = tx.index("spin_lock_irqsave(&eth->reset_queue_lock, flags)")
    tx_status = tx.index("!mtk_hw_reset_check(eth)")
    tx_queue = tx.index("__mtk_queue_reset_work(eth);")
    tx_unlock = tx.index("spin_unlock_irqrestore(&eth->reset_queue_lock, flags)", tx_queue)
    if not tx_lock < tx_status < tx_queue < tx_unlock:
        raise ValueError("tx_timeout MMIO check/queue must remain inside reset state lock")
    if "mtk_queue_reset_work(eth);" not in monitor:
        raise ValueError("monitor pending_work producer does not use the guarded helper")

    lock = stop.index("spin_lock_irqsave(&eth->reset_queue_lock, flags)")
    latch = stop.index("eth->reset_queue_stopping = true;")
    unlock = stop.index("spin_unlock_irqrestore(&eth->reset_queue_lock, flags)")
    cancel_pending = stop.index("cancel_work_sync(&eth->pending_work);")
    cancel_monitor = stop.index("cancel_delayed_work_sync(&eth->reset.monitor_work);")
    if not lock < latch < unlock < cancel_pending < cancel_monitor:
        raise ValueError("stop latch and synchronous cancellation ordering is invalid")
    if "spin_lock_irqsave(&eth->reset_queue_lock, flags)" not in monitor:
        raise ValueError("monitor self-rearm is not serialized")
    monitor_if = monitor.index("if (!eth->reset_queue_stopping)")
    monitor_queue = monitor.index("schedule_delayed_work(&eth->reset.monitor_work")
    monitor_unlock = monitor.index("spin_unlock_irqrestore(&eth->reset_queue_lock, flags)", monitor_queue)
    if not monitor_if < monitor_queue < monitor_unlock:
        raise ValueError("monitor self-rearm is not gated by stop latch")

    remove_stop = remove.index("mtk_stop_reset_work(eth);")
    remove_device_stop = remove.index("mtk_stop(eth->netdev[i]);")
    remove_hw_deinit = remove.index("mtk_hw_deinit(eth);")
    if not remove_stop < remove_device_stop < remove_hw_deinit:
        raise ValueError("remove must stop/drain work before netdev and hardware teardown")

    lock_init = probe.index("spin_lock_init(&eth->reset_queue_lock);")
    stop_init = probe.index("eth->reset_queue_stopping = false;")
    work_init = probe.index("INIT_WORK(&eth->pending_work, mtk_pending_work);")
    if not lock_init < stop_init < work_init:
        raise ValueError("reset queue state must be initialized before work becomes usable")
    err_cleanup = probe.index("err_deinit_ppe:")
    if not work_init < err_cleanup:
        raise ValueError("probe unwind must not cancel an uninitialized work item")
    unwind_stop = probe.index("mtk_stop_reset_work(eth);", err_cleanup)
    unwind_free = probe.index("mtk_free_dev(eth);", err_cleanup)
    if not err_cleanup < unwind_stop < unwind_free:
        raise ValueError("probe unwind must drain work before freeing netdev resources")
    for teardown in ("unregister_netdev(eth->netdev[i]);", "mtk_ppe_deinit(eth);"):
        if not unwind_stop < probe.index(teardown, err_cleanup):
            raise ValueError(f"probe unwind must drain work before {teardown}")
    if "registered_netdevs" not in probe or "test_bit(i, &registered_netdevs)" not in probe:
        raise ValueError("partial probe unwind does not distinguish registered netdevs")

    if "spinlock_t\t\t\treset_queue_lock;" not in h or "bool\t\t\t\treset_queue_stopping;" not in h:
        raise ValueError("reset queue state fields are missing from mtk_eth")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    try:
        check(args.source)
    except (OSError, ValueError) as exc:
        print(f"RFC SERIES STATIC CHECK FAIL: {exc}", file=sys.stderr)
        return 1
    print("RFC SERIES STATIC CHECK PASS (not runtime validation)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
