import asyncio
import time

from config import get_settings
from logging_utils import configure_json_logging
from sqs import JobQueue

from worker_app.health import start_health_server
from worker_app.runner import run_analysis


def poll_forever() -> None:
    configure_json_logging()
    settings = get_settings()
    queue = JobQueue(settings.sqs_queue_url)
    start_health_server()
    while True:
        jobs = queue.receive_jobs(max_messages=1, wait_seconds=20)
        for job in jobs:
            asyncio.run(run_analysis(**job["body"]))
            queue.delete_message(job["receipt_handle"])
        if not jobs:
            time.sleep(1)

if __name__ == "__main__":
    poll_forever()
