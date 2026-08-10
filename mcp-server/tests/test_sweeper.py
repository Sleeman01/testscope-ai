import time

from sweeper import start_sweeper


def test_sweeper_removes_stale_dirs(tmp_path):
    root = tmp_path / "workspace_root"
    stale = root / "old-analysis"
    stale.mkdir(parents=True)
    old_time = time.time() - 7200
    import os
    os.utime(stale, (old_time, old_time))

    thread = start_sweeper(root, interval_seconds=0.1, max_age_seconds=3600)
    time.sleep(0.3)
    assert not stale.exists()
    thread_stop_event_cleanup(thread)  # see implementation note in Step 3

def thread_stop_event_cleanup(thread):
    # start_sweeper returns a daemon thread; test process exit reaps it.
    # No explicit stop needed for this unit test's lifetime.
    pass
