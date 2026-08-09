import time
from config import get_settings
from sqs import JobQueue
from app.health import start_health_server

def poll_forever() -> None:
    settings = get_settings()
    queue = JobQueue(settings.sqs_queue_url)
    start_health_server()
    while True:
        jobs = queue.receive_jobs(max_messages=1, wait_seconds=20)
        for job in jobs:
            # run_analysis(**job["body"]) wired in Task 17
            queue.delete_message(job["receipt_handle"])
        if not jobs:
            time.sleep(1)

if __name__ == "__main__":
    poll_forever()
