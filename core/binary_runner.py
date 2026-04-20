import subprocess
import threading
from typing import List, Optional, Tuple

from core.tiered_logger import get_logger

logger = get_logger("binary_runner")

class CoreBinaryRunner:
    """
    A managed wrapper around subprocess.run that enforces a timeout
    and automatically pipes stdout/stderr to the tiered_logger.
    To be used by privileged plugins to safely execute binaries.
    """

    @classmethod
    def run_binary(cls, cmd_list: List[str], timeout: float = 30.0, cwd: Optional[str] = None) -> Tuple[int, str, str]:
        """
        Executes a binary and returns its exit code, stdout, and stderr.

        Args:
            cmd_list: The command and its arguments.
            timeout: The maximum execution time in seconds.
            cwd: Optional working directory.

        Returns:
            Tuple of (returncode, stdout, stderr).
        """
        logger.info(f"Running binary: {' '.join(cmd_list)}")
        try:
            process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd
            )

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
