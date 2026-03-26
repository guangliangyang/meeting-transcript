"""Base transcriber interface."""

from abc import ABC, abstractmethod
from typing import Callable, Optional


class BaseTranscriber(ABC):
    """Abstract base class for transcription implementations."""

    def __init__(self, on_transcript: Optional[Callable[[str], None]] = None):
        """Initialize transcriber.

        Args:
            on_transcript: Callback called with new transcript text
        """
        self.on_transcript = on_transcript

    @abstractmethod
    def start(self) -> None:
        """Start capturing and transcribing audio."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop capturing."""
        pass

    @abstractmethod
    def get_full_transcript(self) -> str:
        """Get the complete transcript.

        Returns:
            Full transcript as string
        """
        pass

    @abstractmethod
    def get_recent_transcript(self, last_n: int = 10) -> str:
        """Get the last N transcript entries.

        Args:
            last_n: Number of recent entries to return

        Returns:
            Recent transcript entries as string
        """
        pass

    def clear(self) -> None:
        """Clear all transcript data. Optional override."""
        pass

    def save_transcript(self, filepath: str) -> None:
        """Save transcript to a file. Optional override."""
        pass
