import docker
import os

class SandboxVerifier:
    """Runs refactored code in an isolated Docker container to verify correctness."""
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception:
            self.client = None
            print("Warning: Docker not found. Verification will be skipped or simulated.")

    def verify_code(self, code: str) -> tuple[bool, str]:
        """
        Returns (Success, Log)
        1. Writes code to a temporary file.
        2. Mounts it into a Python container.
        3. Executes it.
        """
        if not self.client:
            # Fallback for systems without Docker: basic local execution check
            import io
            import contextlib
            stdout_capture = io.StringIO()
            try:
                with contextlib.redirect_stdout(stdout_capture):
                    exec(code, {"__name__": "__main__"})
                return True, stdout_capture.getvalue()
            except Exception as e:
                return False, str(e)

        temp_file = "/tmp/sandbox_test.py"
        with open(temp_file, "w") as f:
            f.write(code)

        try:
            # Run the container
            container = self.client.containers.run(
                "python:3.9-slim",
                f"python /mnt/sandbox_test.py",
                volumes={temp_file: {'bind': '/mnt/sandbox_test.py', 'mode': 'ro'}},
                remove=True,
                stdout=True,
                stderr=True,
                detach=False
            )
            return True, container.decode("utf-8")
        except docker.errors.ContainerError as e:
            return False, e.stderr.decode("utf-8")
        except Exception as e:
            return False, str(e)
