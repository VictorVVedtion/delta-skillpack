"""Ralph live dashboard for execution status."""
from __future__ import annotations

from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table


class RalphDashboard:
    """Ralph execution live dashboard."""

    def __init__(self, prd):
        self.prd = prd
        self.layout = self._build_layout()
        self.live = Live(self.layout, refresh_per_second=2)
        self.log_lines: list[str] = []

    def _build_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=5),
        )
        layout["main"].split_row(
            Layout(name="stories"),
            Layout(name="log"),
        )
        return layout

    def update(self, current_story=None, log_line: str | None = None) -> None:
        """Update dashboard panels."""
        if log_line:
            self.log_lines.append(log_line)

        completion = self.prd.completion_rate * 100
        self.layout["header"].update(
            Panel(
                f"[bold]Ralph Automation - {self.prd.title}[/] | "
                f"Completion: {completion:.1f}%"
            )
        )

        table = Table(title="Stories")
        table.add_column("ID")
        table.add_column("Title")
        table.add_column("Status")
        table.add_column("Attempts")
        for story in self.prd.stories:
            status = "[green]PASS[/]" if story.passes else "[yellow]PENDING[/]"
            if current_story and story.id == current_story.id:
                status = f"[cyan]RUNNING: {current_story.current_step}[/]"
            table.add_row(story.id, story.title[:20], status, str(story.attempts))
        self.layout["stories"].update(Panel(table))

        self.layout["log"].update(Panel("\n".join(self.log_lines[-15:]), title="Recent Log"))

    def __enter__(self):
        self.live.__enter__()
        return self

    def __exit__(self, *args):
        self.live.__exit__(*args)
