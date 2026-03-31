"""Dev advisor using AI provider."""

import threading
from typing import Callable, Optional
from ai.factory import get_provider
from config import get_advisor_prompt


class DevAdvisor:
    """Provides software development advice based on meeting context."""

    def __init__(self, on_advice: Optional[Callable[[str], None]] = None):
        """
        Initialize dev advisor.

        Args:
            on_advice: Callback called with advice text
        """
        self.on_advice = on_advice
        self._lock = threading.Lock()
        self._advice_history: list[str] = []

        # Get AI provider (Gemini with Grok fallback)
        self._provider = get_provider()

    def get_advice(self, meeting_context: str, specific_question: str = "") -> str:
        """
        Get software development advice based on meeting context.

        Args:
            meeting_context: Recent transcript from the meeting
            specific_question: Optional specific question to answer

        Returns:
            Development advice with web search results
        """
        if not meeting_context.strip():
            return "No meeting context available yet. Keep discussing!"

        try:
            # Build the prompt
            if specific_question:
                prompt = get_advisor_prompt('specific_question').format(
                    meeting_context=meeting_context,
                    specific_question=specific_question
                )
            else:
                prompt = get_advisor_prompt('full_advice').format(
                    meeting_context=meeting_context
                )

            # Generate response
            advice = self._provider.generate(prompt)
            if not advice:
                advice = "Unable to generate advice."

            with self._lock:
                self._advice_history.append(advice)

            if self.on_advice:
                self.on_advice(advice)

            return advice

        except Exception as e:
            error_msg = f"Error getting advice: {e}"
            print(error_msg)
            return error_msg

    def get_quick_answer(self, meeting_context: str) -> str:
        """Get a quick, concise answer for the current discussion topic."""
        if not meeting_context.strip():
            return "No context available."

        try:
            prompt = get_advisor_prompt('quick_answer').format(
                meeting_context=meeting_context
            )

            response = self._provider.generate(prompt)
            return response if response else "No suggestion available."

        except Exception as e:
            return f"Error: {e}"

    def get_advice_history(self) -> list[str]:
        """Get all advice given during this session."""
        with self._lock:
            return self._advice_history.copy()

    def clear_history(self) -> None:
        """Clear advice history."""
        with self._lock:
            self._advice_history.clear()
