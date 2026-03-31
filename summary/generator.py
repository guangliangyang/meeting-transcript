"""Meeting summary generator using AI provider."""

from datetime import datetime
from pathlib import Path
from ai.factory import get_provider
from config import OUTPUT_DIR, get_summary_prompt


class SummaryGenerator:
    """Generates meeting summaries from transcripts."""

    def __init__(self):
        """Initialize summary generator."""
        self._provider = get_provider()

    def generate_summary(self, transcript: str, advice_history: list[str] = None) -> str:
        """
        Generate a comprehensive meeting summary.

        Args:
            transcript: Full meeting transcript
            advice_history: List of AI advice given during the meeting

        Returns:
            Meeting summary text
        """
        if not transcript.strip():
            return "No transcript available to summarize."

        try:
            # Build context with advice if available
            context = f"Meeting Transcript:\n{transcript}"

            if advice_history:
                advice_text = "\n\n".join(advice_history)
                context += f"\n\nAI Advice Given During Meeting:\n{advice_text}"

            prompt = get_summary_prompt('generate_summary').format(context=context)

            response = self._provider.generate(prompt)
            return response if response else "Unable to generate summary."

        except Exception as e:
            return f"Error generating summary: {e}"

    def save_meeting(self, transcript: str, summary: str,
                     advice_history: list[str] = None) -> Path:
        """
        Save complete meeting record to file.

        Args:
            transcript: Full transcript
            summary: Generated summary
            advice_history: AI advice given during meeting

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"meeting_{timestamp}.md"
        filepath = OUTPUT_DIR / filename

        content = [
            f"# Meeting Notes - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
            summary,
            "",
            "---",
            "",
            "## Full Transcript",
            "",
            transcript,
        ]

        if advice_history:
            content.extend([
                "",
                "---",
                "",
                "## AI Advice During Meeting",
                "",
            ])
            for i, advice in enumerate(advice_history, 1):
                content.extend([
                    f"### Advice #{i}",
                    advice,
                    "",
                ])

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))

        return filepath

    def generate_action_items(self, transcript: str) -> str:
        """Extract action items from transcript."""
        if not transcript.strip():
            return "No transcript available."

        try:
            prompt = get_summary_prompt('action_items').format(transcript=transcript)

            response = self._provider.generate(prompt)
            return response if response else "No action items found."

        except Exception as e:
            return f"Error extracting action items: {e}"
