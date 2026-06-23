from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable

class RedteamTUI(App):
    """Basic TUI for viewing redteam results."""

    CSS_PATH = "app.css"

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="results")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Scenario", "Passed", "Policy", "Detectors")
        # Placeholder row
        table.add_row("base64_exfil", "✅", "block", "encoded_canary")


if __name__ == "__main__":
    RedteamTUI().run()
