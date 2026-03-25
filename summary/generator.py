"""Meeting summary generator using Gemini."""

from datetime import datetime
from pathlib import Path
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, OUTPUT_DIR


class SummaryGenerator:
    """Generates meeting summaries from transcripts."""

    def __init__(self):
        """Initialize summary generator."""
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel(GEMINI_MODEL)

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

            prompt = f"""{context}

Please generate a comprehensive meeting summary with the following sections:

## Meeting Summary

### Key Discussion Points
- List the main topics discussed

### Decisions Made
- List any decisions or conclusions reached

### Action Items
- List any tasks or follow-ups mentioned

### Technical Topics
- Summarize any technical discussions
- Include relevant architecture decisions
- Note any libraries/tools mentioned

### Questions Raised
- List any unresolved questions or concerns

### Next Steps
- Summarize what needs to happen next

Keep the summary concise but comprehensive."""

            response = self._model.generate_content(prompt)
            return response.text.strip() if response.text else "Unable to generate summary."

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
            prompt = f"""From this meeting transcript, extract a list of action items:

{transcript}

Format as a checklist:
- [ ] Action item 1 (who is responsible if mentioned)
- [ ] Action item 2
etc.

Only include actual action items, not general discussion points."""

            response = self._model.generate_content(prompt)
            return response.text.strip() if response.text else "No action items found."

        except Exception as e:
            return f"Error extracting action items: {e}"
