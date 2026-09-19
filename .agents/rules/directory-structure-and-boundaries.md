# EchoSync Directory Structure & Separation of Concerns

**Status:** Mandatory for all autonomous execution.
**Objective:** Enforce strict domain isolation, prevent logic bleed across layers, and eliminate lazy scripting. As the Principal Systems Architect dictates, these boundaries are absolute.

## 1. The Core Engine (`/core`)
- **Scope:** Deep computational work, matching engines, task managers, SDKs, and the Nexus framework. 
- **Rule:** This is the heart of EchoSync (~70% of the app). Code here must be transport-agnostic (no HTTP/FastAPI logic) and database-agnostic (no raw SQLAlchemy models). 

## 2. The Orchestration Layer (`/services`)
- **Scope:** Business logic and workflow orchestration. 
- **Rule:** Services glue components together (e.g., fetch from DB -> read file -> dispatch event -> persist). **No deep logic belongs here.** Do not write complex math, regex parsing, or raw metadata extraction in this layer; delegate those to `/core`.

## 3. The Transport Layer (`/web`)
- **Scope:** FastAPI endpoint definitions and API-specific request/response validation.
- **Rule:** Endpoints must be extremely thin. If you are writing a `for` loop or a database query directly in a FastAPI route, you are violating the architecture. Route requests to a reusable service immediately.

## 4. The Accelerator (`/src`)
- **Scope:** Rust (PyO3/FFI) high-performance components and file I/O.
- **Rule:** Acts as the native backend to `/core`.

## 5. The Persistence Layer (`/database`)
- **Scope:** SQLAlchemy models, Alembic migrations, and database sessions. 
- **Rule:** Anything that interacts directly with SQLite schema or ORM mapping belongs here. 

## 6. Plugins (`/plugins`)
- **Scope:** Isolated, agnostic extensions.
- **Rule:** Plugins only communicate with EchoSync via the Nexus framework and event bus. They may mount their own FastAPI endpoints and custom DBs, but they must NEVER directly import from `/services`, `/web`, or other plugins.

## 7. The Anti-Laziness Scripting Constraint (`/scripts` & `/scratch`)
- **Rule:** You are STRICTLY FORBIDDEN from writing disposable, one-off Python scripts to accomplish tasks that can be done using existing CLI tools or by writing a proper unit test in `/tests`. 
- If a utility is broadly useful, build it properly in `/tools` or `/utils`. Do not pollute `/scripts` or the root directory with lazy throwaway code.