import subprocess
import threading
from typing import List, Optional, Tuple

from core.tiered_logger import get_logger
from core.task_manager.models import OwnerType, ProcessOwner
from core.task_manager.supervisor import supervisor

logger = get_logger("binary_runner")


class CoreBinaryRunner:
    """
    A managed wrapper around subprocess.run that enforces a timeout,
    registers the active process PID with the ProcessSupervisor,
    and automatically pipes stdout/stderr to the tiered_logger.
    To be used by privileged plugins and core to safely execute binaries.
    """

    @classmethod
    def run_binary(
        cls,
        cmd_list: List[str],
        timeout: float = 30.0,
        cwd: Optional[str] = None,
        owner_id: str = "core.binary_runner",
        owner_type: OwnerType = OwnerType.CORE,
    ) -> Tuple[int, str, str]:
        """
        Executes a binary and returns its exit code, stdout, and stderr.
        Registers process PID with supervisor during execution.

        Args:
            cmd_list: The command and its arguments.
            timeout: The maximum execution time in seconds.
            cwd: Optional working directory.
            owner_id: Identifier of the component running the process.
            owner_type: Type of owner (CORE, PLUGIN, SYSTEM_JOB).

        Returns:
            Tuple of (returncode, stdout, stderr).
        """
        logger.info(f"Running binary: {' '.join(cmd_list)}")
        reg_id = None
        try:
            process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd
            )

            # Automatically register process PID with supervisor
            owner_info = ProcessOwner(
                owner_id=owner_id,
                owner_type=owner_type,
                pid=process.pid,
                task_name=cmd_list[0] if cmd_list else "unknown_binary",
                metadata={"cmd": cmd_list, "cwd": cwd}
            )
            reg_id = supervisor.register_process(owner_info)

            stdout_lines = []
            stderr_lines = []

            def read_stream(stream, lines, log_level):
                for line in stream:
                    line = line.strip()
                    if line:
                        lines.append(line)
                        if log_level == 'info':
                            logger.info(f"[{cmd_list[0]} stdout] {line}")
                        else:
                            logger.error(f"[{cmd_list[0]} stderr] {line}")

            stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, stdout_lines, 'info'))
            stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, stderr_lines, 'error'))

            stdout_thread.start()
            stderr_thread.start()

            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                logger.error(f"Binary execution timed out after {timeout}s: {' '.join(cmd_list)}")
                return -1, "\n".join(stdout_lines), f"TimeoutExpired: Process killed after {timeout} seconds."

            stdout_thread.join()
            stderr_thread.join()

            logger.info(f"Binary execution completed with return code {process.returncode}")
            return process.returncode, "\n".join(stdout_lines), "\n".join(stderr_lines)

        except Exception as e:
            logger.exception(f"Failed to execute binary: {' '.join(cmd_list)}")
            return -1, "", str(e)
        finally:
            if reg_id:
                supervisor.unregister_process(reg_id)
