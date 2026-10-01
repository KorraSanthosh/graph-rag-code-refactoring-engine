import logging
import os
import subprocess
import sys
import tempfile

logger = logging.getLogger(__name__)


class SandboxVerifier:
    """
    Executes untrusted (LLM-generated) code in isolation.

    Modes, reported by `mode`:
      - "docker": throwaway container (no network, memory/CPU/pid limits, read-only FS,
        all capabilities dropped). Code is passed via `python -c`, so it also works when
        the app itself runs in a container that talks to the host Docker socket.
      - "subprocess": fallback when Docker is unavailable — a separate isolated Python
        process with a timeout. NOT a security boundary; for local development only.
      - "disabled": no execution at all (set SANDBOX_FALLBACK=disabled in production
        environments without Docker).
    """

    def __init__(
        self,
        docker_image: str = "python:3.11-slim",
        timeout: int = 30,
        fallback: str | None = None,
    ):
        self.docker_image = docker_image
        self.timeout = timeout
        self.fallback = (fallback or os.getenv("SANDBOX_FALLBACK", "subprocess")).lower()
        self._client = None
        self._docker_available = False
        self._init_docker()

    @property
    def mode(self) -> str:
        if self._docker_available:
            return "docker"
        return "disabled" if self.fallback == "disabled" else "subprocess"

    def _init_docker(self) -> None:
        try:
            import docker

            self._client = docker.from_env()
            self._client.ping()
            self._docker_available = True
            logger.info("Docker sandbox initialized.")
        except Exception as e:
            logger.warning(f"Docker unavailable ({e}). Sandbox mode: {self.mode}.")

    def verify_code(self, code: str) -> tuple[bool, str]:
        """Returns (success, log). Success means the code ran and exited with status 0."""
        if self._docker_available:
            return self._verify_in_docker(code)
        if self.fallback == "disabled":
            return False, "Sandbox unavailable: Docker is not reachable and fallback is disabled."
        return self._verify_in_subprocess(code)

    def _verify_in_docker(self, code: str) -> tuple[bool, str]:
        container = None
        try:
            container = self._client.containers.run(
                self.docker_image,
                ["python", "-I", "-c", code],
                detach=True,
                network_disabled=True,
                mem_limit="128m",
                nano_cpus=500_000_000,
                pids_limit=64,
                read_only=True,
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"],
            )
            result = container.wait(timeout=self.timeout)
            output = container.logs(stdout=True, stderr=True).decode("utf-8", "replace")
            return result.get("StatusCode", 1) == 0, output
        except Exception as e:
            # wait() timeouts surface as requests/urllib3 errors; treat all as failure.
            logger.warning(f"Docker verification failed: {e}")
            if container is not None:
                try:
                    container.kill()
                except Exception:
                    pass
            msg = str(e)
            if "timed out" in msg.lower():
                msg = f"Execution timed out after {self.timeout}s."
            return False, msg
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    def _verify_in_subprocess(self, code: str) -> tuple[bool, str]:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                proc = subprocess.run(
                    [sys.executable, "-I", "-c", code],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=tmp,
                    env={"PATH": os.environ.get("PATH", "")},
                )
            return proc.returncode == 0, (proc.stdout + proc.stderr)
        except subprocess.TimeoutExpired:
            return False, f"Execution timed out after {self.timeout}s."
        except Exception as e:
            return False, str(e)
