from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Input, LoadingIndicator, Select, Static, TabbedContent, TabPane
from textual.widgets._select import SelectCurrent, SelectOverlay

from dataset import POINT_VALUES, dataset_dictionary, search_players
from predict_score import predict_player, predict_season


MIN_PREDICTION_SEASON = min(dataset_dictionary) + 1
MAX_PREDICTION_SEASON = max(dataset_dictionary) + 1
SEASON_OPTIONS = [
    (f"{year}-{str(year + 1)[-2:]}", year)
    for year in range(MAX_PREDICTION_SEASON, MIN_PREDICTION_SEASON - 1, -1)
]
POINT_FIELDS = (
    ("goals", "GOALS"),
    ("assists", "ASSISTS"),
    ("shots", "SHOTS"),
    ("blocks", "BLOCKS"),
    ("hits", "HITS"),
    ("powerplay_goals", "POWER PLAY GOALS"),
    ("shorthanded_goals", "SHORTHANDED GOALS"),
)
STAT_COLUMNS = ("FANTASY SCORE", "GP", "G", "A", "P", "PPG", "SHG", "SOG", "H", "B")


class TabSelect(Select):
    class TeamSelectOverlay(SelectOverlay):
        BINDINGS = [
            *SelectOverlay.BINDINGS,
            Binding("tab", "select", "Select", show=False),
        ]

    def compose(self) -> ComposeResult:
        yield SelectCurrent(self.prompt)
        yield self.TeamSelectOverlay(type_to_search=self._type_to_search).data_bind(
            compact=Select.compact
        )


class FantasyApp(App):
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [("q", "quit", "Quit")]

    CSS = """
    Screen { background: $surface; }
    .controls { height: auto; padding: 1; background: $panel; }
    .field { width: 1fr; height: auto; margin-right: 1; }
    .field-label { padding: 0 0 0 1; text-style: bold; color: $text-muted; }
    .field Input, .field Select { width: 1fr; }
    .field-button { width: auto; height: auto; }
    .results { padding: 1; }
    .result-title { padding: 0 0 1 0; text-style: bold; color: $accent; }
    .empty-state { padding: 1 0; color: $text-muted; }
    .point-grid { height: auto; padding: 1; }
    .point-field { width: 30; height: auto; margin: 0 1 1 0; }
    .point-field Input { width: 12; }
    DataTable { height: 1fr; margin: 0 1; }
    LoadingIndicator { height: 3; }
    .hidden { display: none; }
    """

    def compose(self) -> ComposeResult:
        with TabbedContent(initial="season"):
            with TabPane("PREDICT SEASON", id="season"):
                yield from self._season_pane()
            with TabPane("PREDICT PLAYER", id="player"):
                yield from self._player_pane()
            with TabPane("PLAYER SEARCH", id="search"):
                yield from self._search_pane()
            with TabPane("EDIT POINT VALUES", id="points"):
                yield from self._points_pane()
        yield Footer()

    def _season_pane(self):
        yield Horizontal(
            Vertical(Static("SEASON", classes="field-label"), TabSelect(SEASON_OPTIONS, value=MAX_PREDICTION_SEASON, allow_blank=False, id="season-input"), classes="field"),
            Vertical(Static("", classes="field-label"), Button("RUN", id="season-run", variant="primary"), classes="field-button"),
            classes="controls",
        )
        yield LoadingIndicator(id="season-loading", classes="hidden")
        yield VerticalScroll(id="season-results", classes="results")

    def _player_pane(self):
        yield Horizontal(
            Vertical(Static("SEASON", classes="field-label"), TabSelect(SEASON_OPTIONS, value=MAX_PREDICTION_SEASON, allow_blank=False, id="player-season"), classes="field"),
            Vertical(Static("PLAYER ID", classes="field-label"), Input(placeholder="use PLAYER SEARCH to find ID", id="player-id"), classes="field"),
            Vertical(Static("", classes="field-label"), Button("RUN", id="player-run", variant="primary"), classes="field-button"),
            classes="controls",
        )
        yield LoadingIndicator(id="player-loading", classes="hidden")
        yield VerticalScroll(id="player-results", classes="results")

    def _points_pane(self):
        yield Button("SAVE POINT VALUES", id="points-save", variant="primary")
        yield Vertical(
            *(Vertical(Static(label, classes="field-label"), Input(value=str(POINT_VALUES[key]), id=f"value-{key}"), classes="point-field") for key, label in POINT_FIELDS),
            classes="point-grid",
        )
        yield Static("", id="points-status", classes="empty-state")

    def _search_pane(self):
        yield Horizontal(
            Vertical(Static("PLAYER NAME", classes="field-label"), Input(placeholder="search by first or last name", id="search-name"), classes="field"),
            Vertical(Static("", classes="field-label"), Button("SEARCH", id="search-run", variant="primary"), classes="field-button"),
            classes="controls",
        )
        yield VerticalScroll(id="search-results", classes="results")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "season-input":
            await self.run_season()
        elif event.input.id in {"player-season", "player-id"}:
            await self.run_player()
        elif event.input.id == "search-name":
            await self.search_player()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        actions = {
            "season-run": self.run_season,
            "player-run": self.run_player,
            "search-run": self.search_player,
            "points-save": self.save_points,
        }
        action = actions.get(event.button.id)
        if action:
            await action()

    async def _call(self, function, *args):
        return await asyncio.get_running_loop().run_in_executor(None, function, *args)

    def _season_year(self, input_id: str) -> int | None:
        value = self.query_one(f"#{input_id}", Select).value
        try:
            return int(value)
        except (TypeError, ValueError):
            self.notify("select a season", severity="warning")
            return None

    async def run_season(self) -> None:
        season = self._season_year("season-input")
        if season is None or season - 1 not in dataset_dictionary:
            self.notify(
                f"season must be between {MIN_PREDICTION_SEASON}-{str(MIN_PREDICTION_SEASON + 1)[-2:]} "
                f"and {MAX_PREDICTION_SEASON}-{str(MAX_PREDICTION_SEASON + 1)[-2:]}",
                severity="warning",
            )
            return
        await self._show_loading("season", True)
        results = self.query_one("#season-results", VerticalScroll)
        await results.remove_children()
        try:
            ranking, accuracy = await self._call(predict_season, season, "all")
        except Exception as exc:
            await results.mount(Static(f"prediction failed: {exc}", classes="empty-state"))
        else:
            await results.mount(Static(f"{season}-{str(season + 1)[-2:]} Predictions", classes="result-title"))
            table = DataTable(zebra_stripes=True)
            table.add_columns("RANK", "PLAYER", "TEAM", "POS", *STAT_COLUMNS)
            for rank, player in enumerate(reversed(ranking), 1):
                table.add_row(str(rank), player.name, player.team, player.position, *self._statline(player))
            await results.mount(table)
            if accuracy is not None:
                await results.mount(Static(f"Historical Accuracy: {1 - accuracy:.1%}"))
        await self._show_loading("season", False)

    async def run_player(self) -> None:
        season = self._season_year("player-season")
        player_id = self.query_one("#player-id", Input).value.strip()
        if season is None or not player_id.isdigit():
            self.notify("enter a numeric player ID", severity="warning")
            return
        await self._show_loading("player", True)
        results = self.query_one("#player-results", VerticalScroll)
        await results.remove_children()
        try:
            player, accuracy = await self._call(predict_player, season, int(player_id), "all")
        except Exception as exc:
            await results.mount(Static(f"prediction failed: {exc}", classes="empty-state"))
        else:
            await results.mount(Static(f"{player.name} ({player.team}, {player.position})", classes="result-title"))
            table = DataTable(zebra_stripes=True)
            table.add_columns(*STAT_COLUMNS)
            table.add_row(*self._statline(player))
            await results.mount(table)
            if accuracy is not None:
                await results.mount(Static(f"Historical Accuracy: {1 - accuracy:.1%}"))
        await self._show_loading("player", False)

    async def search_player(self) -> None:
        name = self.query_one("#search-name", Input).value.strip()
        results = self.query_one("#search-results", VerticalScroll)
        await results.remove_children()
        if not name:
            self.notify("enter a player name to search", severity="warning")
            return
        matches = await self._call(lambda: list(search_players(name)))
        if not matches:
            await results.mount(Static("no players found", classes="empty-state"))
            return
        self.search_player_ids = [player_id for _, _, _, player_id in matches]
        table = DataTable(id="search-table", zebra_stripes=True, cursor_type="row")
        table.add_columns("PLAYER", "TEAM", "POS", "PLAYER ID")
        for player_name, team, position, player_id in matches:
            table.add_row(player_name, team, position, player_id)
        await results.mount(table)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "search-table":
            return
        player_id = self.search_player_ids[event.cursor_row]
        self.copy_to_clipboard(player_id)
        self.notify(f"copied player ID {player_id}")

    async def save_points(self) -> None:
        try:
            values = {key: float(self.query_one(f"#value-{key}", Input).value) for key, _ in POINT_FIELDS}
        except ValueError:
            self.notify("point values must be numbers", severity="warning")
            return
        POINT_VALUES.update(values)
        self.query_one("#points-status", Static).update("")

    def _statline(self, player) -> tuple[str, ...]:
        return (
            f"{player.fantasy_score:.1f}",
            f"{player.games_played:.0f}",
            f"{player.goals:.0f}",
            f"{player.assists:.0f}",
            f"{player.goals + player.assists:.0f}",
            f"{player.powerplay_goals:.0f}",
            f"{player.shorthanded_goals:.0f}",
            f"{player.shots:.0f}",
            f"{player.hits:.0f}",
            f"{player.blocks:.0f}",
        )

    async def _show_loading(self, key: str, visible: bool) -> None:
        indicator = self.query_one(f"#{key}-loading", LoadingIndicator)
        indicator.set_class(not visible, "hidden")


if __name__ == "__main__":
    FantasyApp().run()
