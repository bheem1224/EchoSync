
import core
import time
import logging
import threading
from datetime import datetime

# Setup basic python logging to see output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_logger():
    print("Testing TieredLogger...")
    logger = core.TieredLogger("test_source")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.debug("This is a debug message")
    print("TieredLogger test complete (check logs).")

def test_limiter():
    print("Testing RateLimiter...")
    # 5 tokens max, refills 2 tokens per second
    limiter = core.RateLimiter(5.0, 2.0)

    start = time.time()
    for i in range(10):
        print(f"Request {i+1}: Acquiring 1 token...")
        limiter.acquire(1.0)
        print(f"Request {i+1}: Acquired. Elapsed: {time.time() - start:.2f}s")

    print("RateLimiter test complete.")

def test_scheduler():
    print("Testing Scheduler...")
    scheduler = core.Scheduler()
    scheduler.start()

    def job_1():
        print(f"Job 1 executed at {datetime.now()}")

    def job_2():
        print(f"Job 2 executed at {datetime.now()}")

    def job_write():
        print(f"Write Job started at {datetime.now()}")
        time.sleep(2)
        print(f"Write Job finished at {datetime.now()}")

    def job_read():
        print(f"Read Job started at {datetime.now()}")
        time.sleep(1)
        print(f"Read Job finished at {datetime.now()}")

    # Run every second
    scheduler.register_job("job_1", "* * * * * * *", job_1, [])
    # Run every 2 seconds
    scheduler.register_job("job_2", "*/2 * * * * * *", job_2, [])

    print("Scheduler running simple jobs for 5 seconds...")
    time.sleep(5)

    print("Testing Scheduler Locking...")
    # Schedule conflicting jobs
    # Write job takes 2 seconds. Read job takes 1 second.
    # If locking works, Read Job should not start until Write Job finishes (or vice versa depending on who grabs lock first)
    # But cron schedules are fixed. Let's schedule them to start at the same time.
    # Note: cron resolution is 1 second.

    # We can't easily force them to start exactly now with cron strings in this test script without waiting for the next second.
    # So we will register them and wait.

    print("Registering locking jobs...")
    scheduler.register_job("write_job", "* * * * * * *", job_write, ["write:db"])
    scheduler.register_job("read_job", "* * * * * * *", job_read, ["read:db"])

    print("Waiting for locking jobs to execute (look for non-overlapping execution)...")
    time.sleep(10)

    scheduler.stop()
    print("Scheduler test complete.")

if __name__ == "__main__":
    test_logger()
    print("-" * 20)
    test_limiter()
    print("-" * 20)
    test_scheduler()
