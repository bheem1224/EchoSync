"""AST Diagnostic Scanner: Audit Task Manager & Concurrency Adoption across EchoSync.

Maps every background thread, process instantiation, custom polling loop,
and unmanaged database write across core/, services/, database/, web/, and plugins/.

Generates a structured migration backlog report for alignment with ADR 0001.
"""

from __future__ import annotations

import ast
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    file_path: str
    line_number: int
    severity: str  # "CRITICAL", "MEDIUM", "LOW"
    category: str  # "THREAD_SPAWN", "PROCESS_SPAWN", "EXECUTOR_POOL", "POLLING_LOOP", "UNLEASED_DB_WRITE"
    symbol: str
    details: str
    code_snippet: str
    recommendation: str


class ConcurrencyAndDatabaseVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, source_code: str):
        self.file_path = file_path
        self.rel_path = file_path.as_posix()
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self.findings: list[Finding] = []

        # Track imports and context
        self.has_db_write_lease_imported = "db_write_lease" in source_code or "job_queue" in source_code
        self.enclosing_functions: list[str] = []
        self.current_function_has_write_lease = False

    def _get_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def _node_has_write_lease(self, node: ast.AST) -> bool:
        for n in ast.walk(node):
            if isinstance(n, ast.With):
                for item in n.items:
                    if isinstance(item.context_expr, ast.Call):
                        func = item.context_expr.func
                        if getattr(func, "id", "") == "db_write_lease" or getattr(func, "attr", "") == "db_write_lease":
                            return True
        return False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.enclosing_functions.append(node.name)
        old_lease = self.current_function_has_write_lease
        self.current_function_has_write_lease = self._node_has_write_lease(node)
        self.generic_visit(node)
        self.current_function_has_write_lease = old_lease
        self.enclosing_functions.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.enclosing_functions.append(node.name)
        old_lease = self.current_function_has_write_lease
        self.current_function_has_write_lease = self._node_has_write_lease(node)
        self.generic_visit(node)
        self.current_function_has_write_lease = old_lease
        self.enclosing_functions.pop()

    def visit_Call(self, node: ast.Call) -> Any:
        func_name = ""
        full_attr = ""

        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            parts = []
            curr = node.func
            while isinstance(curr, ast.Attribute):
                parts.append(curr.attr)
                curr = curr.value
            if isinstance(curr, ast.Name):
                parts.append(curr.id)
            full_attr = ".".join(reversed(parts))

        # 1. Unmanaged Thread Spawning
        if func_name == "Thread" or full_attr.endswith("threading.Thread"):
            self.findings.append(
                Finding(
                    file_path=self.rel_path,
                    line_number=node.lineno,
                    severity="CRITICAL",
                    category="THREAD_SPAWN",
                    symbol=full_attr or func_name,
                    details="Direct instantiation of raw OS Thread outside Task Manager.",
                    code_snippet=self._get_snippet(node.lineno),
                    recommendation="Migrate execution to JobQueue.register_job() or dispatch via ProcessSupervisor.",
                )
            )

        # 2. Unmanaged Process Spawning
        elif (func_name == "Process" or full_attr.endswith("multiprocessing.Process")) and not full_attr.startswith(
            "psutil."
        ):
            self.findings.append(
                Finding(
                    file_path=self.rel_path,
                    line_number=node.lineno,
                    severity="CRITICAL",
                    category="PROCESS_SPAWN",
                    symbol=full_attr or func_name,
                    details="Direct instantiation of multiprocessing.Process outside Task Manager.",
                    code_snippet=self._get_snippet(node.lineno),
                    recommendation="Register subprocess with ProcessSupervisor or dispatch as a system job under TaskCategory.DATABASE_WRITE_HEAVY.",
                )
            )

        # 3. Concurrent Futures ThreadPoolExecutor / ProcessPoolExecutor
        elif func_name in ("ThreadPoolExecutor", "ProcessPoolExecutor"):
            self.findings.append(
                Finding(
                    file_path=self.rel_path,
                    line_number=node.lineno,
                    severity="CRITICAL",
                    category="EXECUTOR_POOL",
                    symbol=full_attr or func_name,
                    details=f"Unmanaged {func_name} instance risking thread/process saturation.",
                    code_snippet=self._get_snippet(node.lineno),
                    recommendation="Use JobQueue's two-tier worker pool or dispatch bounded batches.",
                )
            )

        # 4. Asyncio Create Task in Background Services
        elif full_attr in ("asyncio.create_task", "create_task") and not self.rel_path.startswith("web/"):
            self.findings.append(
                Finding(
                    file_path=self.rel_path,
                    line_number=node.lineno,
                    severity="LOW",
                    category="ASYNCIO_TASK",
                    symbol=full_attr or func_name,
                    details="Detached asyncio background task spawned without supervisor registration.",
                    code_snippet=self._get_snippet(node.lineno),
                    recommendation="Ensure task lifecycle and cancellation are tracked via ProcessSupervisor.",
                )
            )

        # 5. Unleased Database Commits
        elif func_name == "commit" and ("session" in full_attr.lower() or "db" in full_attr.lower() or not full_attr):
            # If inside background service/plugin and not in route handler, check for db_write_lease
            is_route = self.rel_path.startswith("web/routes/")
            is_migration = "migration" in self.rel_path.lower()
            if not is_route and not is_migration and not self.current_function_has_write_lease:
                func_context = self.enclosing_functions[-1] if self.enclosing_functions else "module"
                self.findings.append(
                    Finding(
                        file_path=self.rel_path,
                        line_number=node.lineno,
                        severity="MEDIUM",
                        category="UNLEASED_DB_WRITE",
                        symbol=f"{func_context} -> {full_attr or 'commit'}",
                        details="Database commit executed without acquiring scoped db_write_lease().",
                        code_snippet=self._get_snippet(node.lineno),
                        recommendation="Wrap database mutation in 'with job_queue.db_write_lease(task_name=...):'.",
                    )
                )

        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> Any:
        # Detect custom polling loops (while True / while running with sleep)
        has_sleep = False
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                name = ""
                if isinstance(child.func, ast.Attribute):
                    name = child.func.attr
                elif isinstance(child.func, ast.Name):
                    name = child.func.id
                if name == "sleep":
                    has_sleep = True
                    break

        if has_sleep:
            func_context = self.enclosing_functions[-1] if self.enclosing_functions else "module"
            self.findings.append(
                Finding(
                    file_path=self.rel_path,
                    line_number=node.lineno,
                    severity="LOW",
                    category="POLLING_LOOP",
                    symbol=f"{func_context} (while-sleep loop)",
                    details="Ad-hoc polling loop detected with sleep call; risk of busy-wait or drift.",
                    code_snippet=self._get_snippet(node.lineno),
                    recommendation="Replace custom polling loop with a periodic ScheduledJob in JobQueue.",
                )
            )

        self.generic_visit(node)


def scan_codebase(root_dir: Path) -> list[Finding]:
    target_dirs = ["core", "services", "database", "web", "plugins"]
    ignore_subtrees = [
        Path("core/task_manager"),
        Path("tests"),
        Path(".venv"),
        Path("venv"),
        Path("node_modules"),
    ]

    all_findings: list[Finding] = []

    for t_dir in target_dirs:
        dir_path = root_dir / t_dir
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            # Check ignored subtrees
            rel_file = py_file.relative_to(root_dir)
            if any(str(rel_file).replace("\\", "/").startswith(str(ign).replace("\\", "/")) for ign in ignore_subtrees):
                continue

            try:
                source_code = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source_code, filename=str(py_file))
                visitor = ConcurrencyAndDatabaseVisitor(rel_file, source_code)
                visitor.visit(tree)
                all_findings.extend(visitor.findings)
            except Exception as e:
                print(f"Error parsing {rel_file}: {e}", file=sys.stderr)

    return all_findings


def generate_markdown_report(findings: list[Finding], output_path: Path) -> None:
    grouped: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        subsys = f.file_path.split("/")[0] if "/" in f.file_path else "root"
        grouped[subsys].append(f)

    critical_count = sum(1 for f in findings if f.severity == "CRITICAL")
    medium_count = sum(1 for f in findings if f.severity == "MEDIUM")
    low_count = sum(1 for f in findings if f.severity == "LOW")

    lines = [
        "# Task Manager & JobQueue Migration Backlog",
        "",
        "**Generated By:** `scripts/audit_task_manager_adoption.py`  ",
        f"**Total Findings:** {len(findings)} ({critical_count} CRITICAL, {medium_count} MEDIUM, {low_count} LOW)  ",
        "**Governing ADR:** [ADR 0001: Two-Tier Worker Pools, SQLite Write Serialization, and Task Lifecycle Management](file:///c:/Users/bheem/VScode-Projects/EchoSync/docs/agents/adrs/0001-task-manager-and-worker-pools.md)  ",
        "",
        "---",
        "",
        "## 1. Executive Summary & Audit Matrix",
        "",
        "| Subsystem | Critical (Threads/Processes) | Medium (Unleased Writes) | Low (Polling/Async) | Total |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    for subsys, items in sorted(grouped.items()):
        c = sum(1 for i in items if i.severity == "CRITICAL")
        m = sum(1 for i in items if i.severity == "MEDIUM")
        l = sum(1 for i in items if i.severity == "LOW")
        lines.append(f"| `{subsys}/` | {c} | {m} | {l} | {len(items)} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 2. Critical Concurrency Migrations (Unmanaged Threads & Processes)",
            "",
            "These call sites spawn raw OS threads or sub-processes outside the Task Manager's two-tier pools and must be migrated immediately.",
            "",
            "| File | Line | Symbol | Details | Action Required |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
    )

    for f in findings:
        if f.severity == "CRITICAL":
            lines.append(
                f"| [`{f.file_path}:{f.line_number}`](file:///c:/Users/bheem/VScode-Projects/EchoSync/{f.file_path}#L{f.line_number}) "
                f"| L{f.line_number} | `{f.symbol}` | {f.details} | {f.recommendation} |"
            )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Medium Severity: Unleased Database Writes",
            "",
            "These functions execute database mutations against SQLite without acquiring `with job_queue.db_write_lease():`, risking database lock collisions under concurrent workloads.",
            "",
            "| File | Line | Context | Code Snippet | Action Required |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
    )

    for f in findings:
        if f.severity == "MEDIUM":
            snippet = f.code_snippet.replace("|", "\\|")
            lines.append(
                f"| [`{f.file_path}:{f.line_number}`](file:///c:/Users/bheem/VScode-Projects/EchoSync/{f.file_path}#L{f.line_number}) "
                f"| L{f.line_number} | `{f.symbol}` | `{snippet}` | {f.recommendation} |"
            )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Low Severity: Custom Polling Loops & Detached Async Tasks",
            "",
            "| File | Line | Symbol | Details | Recommendation |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
    )

    for f in findings:
        if f.severity == "LOW":
            lines.append(
                f"| [`{f.file_path}:{f.line_number}`](file:///c:/Users/bheem/VScode-Projects/EchoSync/{f.file_path}#L{f.line_number}) "
                f"| L{f.line_number} | `{f.symbol}` | {f.details} | {f.recommendation} |"
            )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 5. Phased Migration Roadmap",
            "",
            "### Phase 1: High-Impact Background Services",
            "1. **`services/download_manager.py`:** Migrate thread pool runner to `JobQueue` general pool with scoped `db_write_lease()`. ",
            "2. **`services/library_watcher.py`:** Wrap filesystem event debounce writes with `db_write_lease()`. ",
            "3. **`services/media_manager.py`:** Route background scan workers through `ProcessSupervisor`. ",
            "",
            "### Phase 2: Plugin Ingress & Provider Workers",
            "1. Standardize plugin background loops in `plugins/EchoSync/` to use `self.sdk.jobs` or `job_queue.register_job()`. ",
            "2. Ensure all plugin database writes route via `self.aliases`, `self.attributes`, or `db_write_lease()`. ",
            "",
            "### Phase 3: Web Route Background Tasks",
            "1. Ensure FastAPI `BackgroundTasks` mutating canonical tracks acquire `db_write_lease()`. ",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[+] Wrote migration backlog report to {output_path}")


def main():
    root_dir = Path.cwd()
    print(f"[*] Starting AST Concurrency & Database Audit across: {root_dir}")
    findings = scan_codebase(root_dir)

    critical = [f for f in findings if f.severity == "CRITICAL"]
    medium = [f for f in findings if f.severity == "MEDIUM"]
    low = [f for f in findings if f.severity == "LOW"]

    print("\n" + "=" * 80)
    print("TASK MANAGER ADOPTION & CONCURRENCY AUDIT REPORT")
    print("=" * 80)
    print(f"Total Files Scanned across core/, services/, database/, web/, plugins/")
    print(f"Total Violations / Candidates: {len(findings)}")
    print(f"  - CRITICAL (Raw Threads / Processes / Pools): {len(critical)}")
    print(f"  - MEDIUM   (Unleased Database Writes):        {len(medium)}")
    print(f"  - LOW      (Ad-hoc Polling Loops / Async):    {len(low)}")
    print("=" * 80)

    if critical:
        print("\n[!] TOP CRITICAL VIOLATIONS (Unmanaged Threads / Processes):")
        for f in critical[:15]:
            print(f"  [{f.category}] {f.file_path}:{f.line_number} -> {f.code_snippet}")

    # Generate Markdown Backlog
    report_file = root_dir / "docs" / "agents" / "task-manager-migration-backlog.md"
    generate_markdown_report(findings, report_file)


if __name__ == "__main__":
    main()
