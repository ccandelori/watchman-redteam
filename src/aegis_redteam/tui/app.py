from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static
from textual.containers import Horizontal

class RedteamTUI(App):
    """Basic TUI for Aegis Redteam results."""

    CSS_PATH = "app.css"
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Aegis Redteam Results", id="title")
        yield DataTable(id="results")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Scenario", "Status", "Policy", "Detectors")
        # Example data
        table.add_row("base64_exfil", "✅", "block", "encoded_canary")
        table.add_row("benign", "✅", "allow", "-")
        table.add_row("leak_first_honeytoken", "❌", "escalate", "text_canary")


if __name__ == "__main__":
    RedteamTUI().run()
