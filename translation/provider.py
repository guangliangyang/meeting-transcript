"""Translation provider interface."""

from abc import ABC, abstractmethod


class TranslationProvider(ABC):
    """Abstract base class for translation providers."""

    # Shown in the startup panel so the user can see which endpoint is in use.
    name = "translation"

    @abstractmethod
    def translate(self, text: str) -> str:
        """Translate text into the configured target language.

        Args:
            text: The text to translate

        Returns:
            The translation, or "" if there was nothing to translate

        Raises:
            Exception: On failure. The caller decides whether to fall back.
        """
        pass
