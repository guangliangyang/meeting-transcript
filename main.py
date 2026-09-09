"""Meeting Assistant - Main entry point."""

import sys
import threading
import keyboard
from config import (
    validate_config,
    HOTKEY_GET_ADVICE,
    HOTKEY_END_MEETING,
    HOTKEY_EXIT,
    ADVICE_CONTEXT_ENTRIES,
    ADVICE_CONTEXT_MAX_CHARS,
    TRANSLATION_MAX_HOLD_SECONDS,
    TRANSLATION_MIN_CHARS,
    TRANSLATION_QUEUE_MAX,
    TRANSLATION_WORKERS,
    TRANSLATION_FAILURE_THRESHOLD,
    TRANSLATION_COOLDOWN_SECONDS,
)
from transcription import get_transcriber
from assistant.advisor import DevAdvisor
from summary.generator import SummaryGenerator
from translation.factory import get_translator, describe_translator
from translation.pipeline import TranslationPipeline
from ui.console import ConsoleUI
from ui.encoding import enable_utf8_console


class MeetingAssistant:
    """Main application orchestrator."""

    def __init__(self):
        """Initialize meeting assistant components."""
        self.ui = ConsoleUI()
        self._translator = get_translator()
        self.translation = TranslationPipeline(
            translator=self._translator,
            on_pair=self.ui.add_transcript_pair,
            workers=TRANSLATION_WORKERS,
            queue_size=TRANSLATION_QUEUE_MAX,
            max_hold_seconds=TRANSLATION_MAX_HOLD_SECONDS,
            min_chars=TRANSLATION_MIN_CHARS,
            failure_threshold=TRANSLATION_FAILURE_THRESHOLD,
            cooldown_seconds=TRANSLATION_COOLDOWN_SECONDS,
        )
        self.transcriber = get_transcriber(on_transcript=self._on_transcript)
        self.advisor = DevAdvisor(on_advice=self._on_advice)
        self.summarizer = SummaryGenerator()

        self._running = False
        self._getting_advice = False
        self._advice_lock = threading.Lock()

    def _on_transcript(self, text: str) -> None:
        """Called when new transcript is available.

        Runs on the caption polling thread, so this must not block - submit()
        only enqueues.
        """
        self.translation.submit(text)

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
            # Sized against the flush cadence: segments are now a few seconds
            # each, so a raw count of 15 would be far too short a window.
            context = self.transcriber.get_recent_transcript(
                last_n=ADVICE_CONTEXT_ENTRIES
            )
            if len(context) > ADVICE_CONTEXT_MAX_CHARS:
                context = context[-ADVICE_CONTEXT_MAX_CHARS:]
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

        # Drain held translations before the summary panel prints, otherwise the
        # last transcript line lands after it.
        self.translation.stop(timeout=5.0)

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

            # Start translation before transcription so the first line is covered
            self.translation.start()
            self.ui.show_translation_status(
                self.translation.enabled, describe_translator(self._translator)
            )

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
        self.translation.stop(timeout=5.0)
        self._cleanup_hotkeys()
        self.ui.show_goodbye()


def main():
    """Main entry point."""
    # Must run before ConsoleUI() constructs rich.Console, which snapshots
    # terminal detection - and before anything tries to print Chinese.
    enable_utf8_console()

    # Run assistant
    assistant = MeetingAssistant()
    assistant.run()


if __name__ == "__main__":
    main()
