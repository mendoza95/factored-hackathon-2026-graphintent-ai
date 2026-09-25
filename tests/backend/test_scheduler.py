from app.backend.core.graph_scheduler import GraphColoringScheduler


def test_graph_coloring_batches():
    scheduler = GraphColoringScheduler()

    scheduler.add_task("Fetch_Tx")
    scheduler.add_task("Fetch_User")
    scheduler.add_task("Write_Dispute")

    # Conflict constraint
    scheduler.add_conflict("Fetch_Tx", "Write_Dispute")

    batches = scheduler.compute_schedule()

    fetch_batch = next(b for b, tasks in batches.items() if "Fetch_Tx" in tasks)
    write_batch = next(b for b, tasks in batches.items() if "Write_Dispute" in tasks)

    assert fetch_batch != write_batch
