"""Console UI using Rich library."""

import threading
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.layout import Layout


class ConsoleUI:
    """Rich console UI for meeting assistant."""

    def __init__(self):
        """Initialize console UI."""
        self.console = Console()
        self._transcript_lines: list[str] = []
        self._current_advice: str = ""
        self._status: str = "Waiting..."
        self._lock = threading.Lock()

    def show_header(self) -> None:
        """Display application header."""
        self.console.clear()
        header = Text()
        header.append("Meeting Assistant", style="bold blue")
        header.append(" - Real-time Transcription & Dev Advice", style="dim")
        self.console.print(Panel(header, border_style="blue"))
        self.console.print()

    def show_hotkeys(self) -> None:
        """Display hotkey instructions."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold cyan")
        table.add_column("Action", style="white")

        table.add_row("Ctrl+Space", "Get dev advice based on discussion")
        table.add_row("Ctrl+Q", "End meeting & generate summary")
        table.add_row("Esc", "Exit application")

        self.console.print(Panel(table, title="Hotkeys", border_style="cyan"))
        self.console.print()

    def show_status(self, status: str) -> None:
        """Update and display current status."""
        with self._lock:
            self._status = status
        self.console.print(f"[dim]Status:[/dim] {status}")

    def show_listening(self) -> None:
        """Show that audio capture is active."""
        self.console.print(
            Panel(
                "[green]Listening to microphone...[/green] "
                "[dim]Speak to see transcription[/dim]",
                border_style="green"
            )
        )
        self.console.print()

    def add_transcript(self, text: str) -> None:
        """Add a transcript line."""
        with self._lock:
            self._transcript_lines.append(text)

        # Display the new transcript
        self.console.print(f"[white]{text}[/white]")

    def show_advice(self, advice: str) -> None:
        """Display AI advice."""
        with self._lock:
            self._current_advice = advice

        self.console.print()
        self.console.print(
            Panel(
                Markdown(advice),
                title="Dev Advice",
                border_style="green",
                padding=(1, 2)
            )
        )
        self.console.print()

    def show_thinking(self, message: str = "Getting advice...") -> None:
        """Show a thinking/loading indicator."""
        self.console.print(f"[yellow]{message}[/yellow]")

    def show_summary(self, summary: str) -> None:
        """Display meeting summary."""
        self.console.print()
        self.console.print(
            Panel(
                Markdown(summary),
                title="Meeting Summary",
                border_style="blue",
                padding=(1, 2)
            )
        )

    def show_saved(self, filepath: str) -> None:
        """Show that meeting was saved."""
        self.console.print()
        self.console.print(
            Panel(
                f"[green]Meeting saved to:[/green]\n{filepath}",
                border_style="green"
            )
        )

    def show_error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(f"[red]Error:[/red] {message}")

    def show_goodbye(self) -> None:
        """Display exit message."""
        self.console.print()
        self.console.print(
            Panel(
                "[blue]Thank you for using Meeting Assistant![/blue]",
                border_style="blue"
            )
        )

    def get_transcript_display(self) -> str:
        """Get formatted transcript for display."""
        with self._lock:
            if not self._transcript_lines:
                return "[dim]No transcript yet...[/dim]"
            # Show last 10 lines
            recent = self._transcript_lines[-10:]
            return "\n".join(recent)

    def clear(self) -> None:
        """Clear the console."""
        self.console.clear()

    def print(self, *args, **kwargs) -> None:
        """Print to console."""
        self.console.print(*args, **kwargs)
