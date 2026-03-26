"""Grok AI Provider via OpenCLI."""

import subprocess
import tempfile
import os
from ai.provider import AIProvider


class GrokProvider(AIProvider):
    """Grok AI provider using OpenCLI browser automation."""

    def __init__(self, timeout: int = 120, use_web: bool = True):
        """Initialize Grok provider.

        Args:
            timeout: Timeout in seconds for Grok response
            use_web: Use web interface mode (more reliable)
        """
        self.timeout = timeout
        self.use_web = use_web

    def generate(self, prompt: str) -> str:
        """Generate response using Grok via OpenCLI with file-based prompt.

        Uses temp file to avoid command line length limits (Windows ~8KB).

        Requires:
            - opencli installed and in PATH
            - User logged into grok.com in browser
        """
        # Write prompt to temp file to avoid command line length limits
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(prompt)
            temp_path = f.name

        try:
            cmd = [
                "opencli", "grok", "ask",
                "--file", temp_path,
                "--timeout", str(self.timeout)
            ]
            if self.use_web:
                cmd.append("--web")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 30
            )

            if result.returncode != 0:
                raise Exception(f"Grok error: {result.stderr}")

            return result.stdout.strip()
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
