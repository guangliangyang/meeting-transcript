"""Meeting Assistant - Main entry point."""

import sys
import threading
import keyboard
from config import (
    validate_config,
    HOTKEY_GET_ADVICE,
    HOTKEY_END_MEETING,
    HOTKEY_EXIT
)
from transcription.realtime import RealtimeTranscriber
from assistant.advisor import DevAdvisor
from summary.generator import SummaryGenerator
from ui.console import ConsoleUI


class MeetingAssistant:
    """Main application orchestrator."""

    def __init__(self):
        """Initialize meeting assistant components."""
        self.ui = ConsoleUI()
        self.transcriber = RealtimeTranscriber(on_transcript=self._on_transcript)
        self.advisor = DevAdvisor(on_advice=self._on_advice)
        self.summarizer = SummaryGenerator()

        self._running = False
        self._getting_advice = False
        self._advice_lock = threading.Lock()

    def _on_transcript(self, text: str) -> None:
        """Called when new transcript is available."""
        self.ui.add_transcript(text)

    def _on_advice(self, advice: str) -> None:
        """Called when advice is generated."""
        self.ui.show_advice(advice)

    def _get_advice_async(self) -> None:
        """Get advice in background thread."""
        with self._advice_lock:
            if self._getting_advice:
                return
            self._getting_advice = True

        try:
            self.ui.show_thinking("Analyzing discussion and searching for solutions...")
            context = self.transcriber.get_recent_transcript(last_n=15)
            self.advisor.get_advice(context)
        finally:
            with self._advice_lock:
                self._getting_advice = False

    def _on_hotkey_advice(self) -> None:
        """Handle advice hotkey press."""
        thread = threading.Thread(target=self._get_advice_async, daemon=True)
        thread.start()

    def _on_hotkey_end(self) -> None:
        """Handle end meeting hotkey."""
        self._end_meeting()

    def _on_hotkey_exit(self) -> None:
        """Handle exit hotkey."""
        self._running = False

    def _end_meeting(self) -> None:
        """End meeting and generate summary."""
        self.ui.show_thinking("Ending meeting and generating summary...")

        # Stop transcription
        self.transcriber.stop()

        # Get full transcript
        transcript = self.transcriber.get_full_transcript()

        if not transcript:
            self.ui.show_error("No transcript available to summarize.")
            self._cleanup()
            sys.exit(0)

        # Generate summary
        advice_history = self.advisor.get_advice_history()
        summary = self.summarizer.generate_summary(transcript, advice_history)

        # Show summary
        self.ui.show_summary(summary)

        # Save to file
        filepath = self.summarizer.save_meeting(transcript, summary, advice_history)
        self.ui.show_saved(str(filepath))

        # Exit application
        self._cleanup()
        sys.exit(0)

    def _setup_hotkeys(self) -> None:
        """Register global hotkeys."""
        keyboard.add_hotkey(HOTKEY_GET_ADVICE, self._on_hotkey_advice)
        keyboard.add_hotkey(HOTKEY_END_MEETING, self._on_hotkey_end)
        keyboard.add_hotkey(HOTKEY_EXIT, self._on_hotkey_exit)

    def _cleanup_hotkeys(self) -> None:
        """Unregister hotkeys."""
        keyboard.unhook_all()

    def run(self) -> None:
        """Run the meeting assistant."""
        try:
            # Validate configuration
            validate_config()

            # Show UI
            self.ui.show_header()
            self.ui.show_hotkeys()

            # Setup hotkeys
            self._setup_hotkeys()

            # Start transcription (uses Windows Speech Recognition)
            self.transcriber.start()
            self.ui.show_listening()

            # Main loop
            self._running = True
            while self._running:
                keyboard.wait()  # Wait for any keypress

        except KeyboardInterrupt:
            self.ui.print("\n[yellow]Interrupted by user[/yellow]")
        except Exception as e:
            self.ui.show_error(str(e))
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources."""
        self._running = False
        self.transcriber.stop()
        self._cleanup_hotkeys()
        self.ui.show_goodbye()


def main():
    """Main entry point."""
    # Run assistant
    assistant = MeetingAssistant()
    assistant.run()


if __name__ == "__main__":
    main()
