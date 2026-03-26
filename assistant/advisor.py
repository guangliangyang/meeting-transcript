"""Dev advisor using AI provider."""

import threading
from typing import Callable, Optional
from ai.factory import get_provider


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
                prompt = f"""Based on this meeting discussion:

{meeting_context}

Specific question: {specific_question}

Please provide software development advice. Include:
1. Direct answer to the question
2. Relevant code examples if applicable
3. Recommended libraries or frameworks
4. Links to documentation or resources

Search the web for the latest information."""
            else:
                prompt = f"""Based on this meeting discussion:

{meeting_context}

Analyze the current software development discussion and provide helpful advice:

1. **Architecture Recommendations**: Suggest design patterns or architectural approaches
2. **Libraries & Tools**: Recommend relevant libraries, frameworks, or tools
3. **Best Practices**: Highlight relevant best practices
4. **Code Suggestions**: Provide code snippets if applicable
5. **Resources**: Link to relevant documentation or tutorials

Focus on the most recent topic being discussed."""

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
            prompt = f"""Based on this recent meeting discussion:

{meeting_context}

Provide a BRIEF (2-3 sentences) software development suggestion or answer for what's currently being discussed. Be direct and actionable."""

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
