# V2.5.0 Full System Audit Report

**Date:** 2024-05-24
**Role:** Senior Lead QA and Security Researcher
**Scope:** Expanded Audit of Application Logic, Reliability, and Security

## Executive Summary
Following the remediation of the Zero-Day vulnerabilities in the Plugin Sandbox, a full-system audit was conducted focusing on logic flaws, race conditions, resource exhaustion, and IO handling. Several moderate-to-high severity issues were discovered that could lead to database corruption, stalled queues, incorrect metadata matching, and system denial of service.

Below are the categorized findings and their conceptual fixes.

---

## 1. Data Integrity & Race Conditions

### 1.1 "Poison Pill" Race Condition in Metadata Enhancer
**Severity:** HIGH
**Location:** `services/metadata_enhancer.py` (Batch Processing Loop)
**Description:** While processing batches of tracks in `enhance_library_metadata`, a hard database lock (`OperationalError: database is locked`) during a `session.commit()` on a single track causes the entire job to crash and raise the exception without completing the batch. Because the job queue retries the same batch, if the lock condition persists or is triggered repeatedly by the same file, the queue gets stuck in an infinite retry loop (a "Poison Pill").
**Conceptual Fix:**
The batch processor should wrap the `session.commit()` in a retry block with exponential backoff specifically for lock errors, and if it ultimately fails, it should `session.rollback()`, skip the track, and continue processing the rest of the batch, rather than immediately crashing the job.

### 1.2 "Zombie Jobs" in the Job Queue
**Severity:** MEDIUM
**Location:** `core/job_queue.py` (`_run_job_thread` and `_is_running` concurrency lock)
**Description:** The job queue uses `_is_running[job.name] = True` to prevent overlapping executions of the same job. If `threading.Thread(target=_run_job_thread).start()` throws an unexpected non-standard exception or if the Python interpreter forcefully kills the thread mid-execution without triggering the `finally` block, the job remains marked as running forever. This permanently disables the job ("Zombie Job") until a server reboot.
**Conceptual Fix:**
Implement a watchdog/timeout mechanism for running jobs. If a job's `last_started` timestamp exceeds a reasonable threshold (e.g., 2 hours) and the job is still marked as `running = True`, the scheduler should forcefully clear the `_is_running` flag and requeue the job.

---

## 2. Matching Engine Edge Cases

### 2.1 Missing Duration False-Positive Exploit
**Severity:** HIGH
**Location:** `core/matching_engine/matching_engine.py` (`_calculate_duration_match`)
**Description:** The matching engine's duration validation logic states:
```python
if not source.duration or not candidate.duration:
    return 1.0
```
If a candidate track (e.g., returned by a poorly behaving plugin) is missing its duration metadata entirely, the engine assumes a perfect 1.0 (100%) match for the duration score. An attacker or buggy plugin can exploit this by returning tracks with missing durations to bypass the strict duration penalties, artificially inflating the final confidence score and causing the system to download the wrong track.
**Conceptual Fix:**
Missing duration should not return a perfect `1.0`. It should either return a neutral score (e.g., `0.5`), apply a penalty, or defer entirely to the fuzzy text score. Alternatively, enforce that candidates without duration cannot exceed a strict confidence ceiling (e.g., max 80%).

---

## 3. Resource Exhaustion (DoS)

### 3.1 Unbounded While-True Loop in Post Processor (Disk DoS)
**Severity:** MEDIUM
**Location:** `core/file_handling/post_processor.py` (`_get_unique_filename`)
**Description:** The logic to handle duplicate files iterates a `while True:` loop to find an available filename:
```python
while True:
    new_name = f"{stem} ({counter}){suffix}"
    ...
    counter += 1
```
If a file system permission error prevents the `exists()` check from resolving correctly, or if there is an extreme edge case where 100,000 duplicates exist, this loop will spin indefinitely, pinning the CPU at 100% and starving the worker thread.
**Conceptual Fix:**
Introduce a hard limit to the loop (e.g., `if counter > 1000: raise MaxRetriesExceededError()`).

### 3.2 Rate Limit Starvation via Shared Session
**Severity:** MEDIUM
**Location:** `core/request_manager.py` (`RateLimitConfig`)
**Description:** Plugins utilize the shared `RequestManager` which enforces a global `RateLimitConfig`. A malicious or poorly coded plugin could spam external API requests (e.g., 1,000 per second). While the rate limiter will slow them down, it fills the internal queue and consumes the global rate limit tokens, effectively starving the core system's metadata fetching jobs (like MusicBrainz or AcoustID queries).
**Conceptual Fix:**
Implement separate rate limit buckets: one strict bucket for community plugins and one prioritized bucket for core system services.

---

## 4. Unhandled IO Scenarios

### 4.1 Cross-Partition Move Corruption
**Severity:** HIGH
**Location:** `core/file_handling/post_processor.py` (`organize_file`) and `core/file_handling/base_io.py`
**Description:** The system uses `shutil.move` to transfer files from the download directory to the final library. If the library is on a different hard drive/partition, `shutil.move` falls back to a `copy2` followed by an `os.unlink`. If the destination drive runs out of disk space halfway through the copy, Python raises an exception. However, a partial, corrupted file is left on the destination drive. The database might assume failure, but the filesystem now contains garbage data.
**Conceptual Fix:**
Wrap the `shutil.move` in a `try/except` block that explicitly checks for `OSError` (like `ENOSPC` - No space left on device). In the `except` block, attempt to aggressively delete the partially written destination file before returning the failure state to the database.
