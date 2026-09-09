"""Gemini AI Provider."""

import google.generativeai as genai
from ai.provider import AIProvider


class GeminiProvider(AIProvider):
    """Google Gemini AI provider."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash",
                 timeout: float | None = None):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key
            model: Model name to use
            timeout: Per-request timeout in seconds. None uses the SDK default,
                which is effectively unbounded and unsuitable for a real-time path.
        """
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)
        self._timeout = timeout

    def generate(self, prompt: str) -> str:
        """Generate response using Gemini."""
        kwargs = {"request_options": {"timeout": self._timeout}} if self._timeout else {}
        response = self._model.generate_content(prompt, **kwargs)
        return response.text.strip() if response.text else ""
