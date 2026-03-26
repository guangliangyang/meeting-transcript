"""AI Provider factory with fallback support."""

from ai.provider import AIProvider
from ai.gemini import GeminiProvider
from ai.grok import GrokProvider
from config import GEMINI_API_KEY, GEMINI_MODEL, GROK_TIMEOUT


class FallbackProvider(AIProvider):
    """Provider that tries Gemini first, falls back to Grok on error."""

    def __init__(self):
        """Initialize with both providers."""
        self._gemini = GeminiProvider(api_key=GEMINI_API_KEY, model=GEMINI_MODEL)
        self._grok = GrokProvider(timeout=GROK_TIMEOUT)

    def generate(self, prompt: str) -> str:
        """Generate response, trying Gemini first then Grok."""
        try:
            return self._gemini.generate(prompt)
        except Exception as e:
            print(f"[WARN] Gemini failed: {e}, falling back to Grok...")
            return self._grok.generate(prompt)


def get_provider() -> AIProvider:
    """Get the configured AI provider with fallback support."""
    return FallbackProvider()
