"""Gemini AI Provider."""

import google.generativeai as genai
from ai.provider import AIProvider


class GeminiProvider(AIProvider):
    """Google Gemini AI provider."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key
            model: Model name to use
        """
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def generate(self, prompt: str) -> str:
        """Generate response using Gemini."""
        response = self._model.generate_content(prompt)
        return response.text.strip() if response.text else ""
