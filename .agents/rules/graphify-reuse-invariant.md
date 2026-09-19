# Universal DRY & Graphify Reuse Invariant

**Status:** Mandatory for all autonomous execution.
**Objective:** Prevent duplication of any utility, orchestration, or logic patterns by forcing a codebase search before authoring new code.

## 1. The Universal Search Mandate
You MUST NEVER write new logic without first verifying if an existing utility handles it. This applies to, but is not limited to:
- Logging (always use existing `tiered_logger`).
- File handling, path formatting, and I/O wrappers.
- String sanitization, regex tokenization, and metadata parsing.
- Authentication, OAuth flows, and token management.
- Task queuing, concurrency management, and database sessions.

## 2. The Upgrade-Over-Bypass Protocol
If you locate an existing component in `core/` or `services/` that handles 80% of your requirement, you are STRICTLY FORBIDDEN from writing a redundant workaround in a different file. 
- You must halt execution.
- You must propose an upgrade to the centralized component.
- You must wait for user authorization before mutating the core architecture.