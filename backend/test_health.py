"""Exercise the real ASGI app over HTTP using only the standard test library."""

import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import URLError
from urllib.request import urlopen


class HealthTest(unittest.TestCase):
    def test_health_over_http(self):
        # Keep an OS-assigned port reserved until Uvicorn takes over the socket.
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "backend.main:app",
                 "--fd", str(listener.fileno()), "--log-level", "warning"],
                cwd=Path(__file__).resolve().parent.parent,
                pass_fds=(listener.fileno(),),
            )
            try:
                deadline = time.monotonic() + 10
                while True:
                    if process.poll() is not None:
                        self.fail("Backend exited before becoming ready")
                    try:
                        with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                            self.assertEqual(response.status, 200)
                            self.assertEqual(response.headers.get_content_type(), "application/json")
                            self.assertEqual(json.load(response), {"status": "ok"})
                        break
                    except (URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            self.fail("Backend did not become ready within 10 seconds")
                        time.sleep(0.05)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
