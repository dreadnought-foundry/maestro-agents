"""Kanban TUI application — interactive terminal board for the kanban directory."""

from __future__ import annotations

import shutil
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option

from kanban_tui.scanner import (
    ColumnInfo,
    EpicInfo,
    SprintInfo,
    scan_kanban,
    write_history_entry,
)

# Epic color palette
EPIC_COLORS = ["cyan", "green", "magenta", "yellow", "blue", "red"]
STANDALONE_COLOR = "white"


def _epic_color(epic_number: int | None) -> str:
    if not isinstance(epic_number, int):
        return STANDALONE_COLOR
    return EPIC_COLORS[epic_number % len(EPIC_COLORS)]


class CardSelected(Message):
    def __init__(self, markdown_content: str, title: str) -> None:
        super().__init__()
        self.markdown_content = markdown_content
        self.title = title


class EpicExpandToggled(Message):
    """Fired when an epic is expanded or collapsed so all columns can sync."""

    def __init__(self, epic_number: int, expanded: bool) -> None:
        super().__init__()
        self.epic_number = epic_number
        self.expanded = expanded


class SprintCard(Static):
    can_focus = True

    def __init__(self, sprint: SprintInfo, color: str, column_name: str, col_index: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sprint = sprint
        self.color = color
        self.column_name = column_name
        self.col_index = col_index

    def compose(self) -> ComposeResult:
        s = self.sprint
        type_badge = f" [dim]{s.sprint_type}[/]" if s.sprint_type else ""
        yield Static(f"[bold {self.color}]S-{s.number:02d}[/] {s.title}{type_badge}")

    def on_focus(self) -> None:
        try:
            content = self.sprint.path.read_text(encoding="utf-8")
        except OSError:
            content = "(unable to read file)"
        self.post_message(CardSelected(content, f"Sprint {self.sprint.number:02d}"))


class EpicCard(Static):
    can_focus = True
    expanded: reactive[bool] = reactive(False)

    def __init__(self, epic: EpicInfo, color: str, column_name: str, col_index: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.epic = epic
        self.color = color
        self.column_name = column_name
        self.col_index = col_index

    def compose(self) -> ComposeResult:
        e = self.epic
        n = len(e.sprints)
        chevron = "v" if self.expanded else ">"
        yield Static(
            f"[bold {self.color}]{chevron} E-{e.number:02d}[/] {e.title} [dim]({n})[/]",
            id=f"epic-header-{e.number}",
        )
        for sprint in e.sprints:
            yield SprintCard(
                sprint, color=self.color, column_name=self.column_name,
                col_index=self.col_index, classes="nested-sprint collapsed",
            )

    def toggle_expanded(self) -> None:
        new_val = not self.expanded
        self.expanded = new_val
        self.post_message(EpicExpandToggled(self.epic.number, new_val))

    def watch_expanded(self, value: bool) -> None:
        # Show/hide nested sprints
        for child in self.query(".nested-sprint"):
            child.set_class(not value, "collapsed")
        # Update chevron
        e = self.epic
        n = len(e.sprints)
        chevron = "v" if value else ">"
        try:
            header = self.query_one(f"#epic-header-{e.number}", Static)
            header.update(f"[bold {self.color}]{chevron} E-{e.number:02d}[/] {e.title} [dim]({n})[/]")
        except Exception:
            pass

    def on_focus(self) -> None:
        epic_md = self.epic.path / "_epic.md"
        try:
            content = epic_md.read_text(encoding="utf-8")
        except OSError:
            content = f"# Epic {self.epic.number:02d}: {self.epic.title}\n\n(no _epic.md)"
        self.post_message(CardSelected(content, f"Epic {self.epic.number:02d}"))


class KanbanColumn(VerticalScroll):
    def __init__(self, column: ColumnInfo, col_index: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.column = column
        self.col_index = col_index

    def compose(self) -> ComposeResult:
        total = len(self.column.standalone_sprints)
        for epic in self.column.epics:
            total += 1 + len(epic.sprints)

        yield Static(
            f"[bold underline]{self.column.display_name}[/] [dim]({total})[/]",
            classes="column-header",
        )

        if total == 0:
            yield Static("[dim]empty[/]", classes="empty-label")
            return

        for epic in self.column.epics:
            color = _epic_color(epic.number)
            yield EpicCard(
                epic, color=color, column_name=self.column.name,
                col_index=self.col_index, classes="card",
            )
        for sprint in self.column.standalone_sprints:
            color = _epic_color(sprint.epic_number) if sprint.epic_number is not None else STANDALONE_COLOR
            yield SprintCard(
                sprint, color=color, column_name=self.column.name,
                col_index=self.col_index, classes="card",
            )


class DetailPanel(VerticalScroll):
    content_text: reactive[str] = reactive("")
    title_text: reactive[str] = reactive("Details")

    def compose(self) -> ComposeResult:
        yield Static("[dim]Select a card to view details[/]", id="detail-content")

    def watch_content_text(self, value: str) -> None:
        try:
            widget = self.query_one("#detail-content", Static)
            widget.update(value)
        except Exception:
            pass

    def watch_title_text(self, value: str) -> None:
        self.border_title = value


class MoveScreen(ModalScreen[str | None]):
    CSS = """
    MoveScreen { align: center middle; }
    #move-dialog {
        width: 40; height: auto; max-height: 20;
        border: solid $primary; background: $surface; padding: 1 2;
    }
    #move-title { text-align: center; padding-bottom: 1; }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, card, current_col: str, columns: list[ColumnInfo], kanban_dir: Path) -> None:
        super().__init__()
        self.card = card
        self.current_col = current_col
        self.all_columns = columns
        self.kanban_dir = kanban_dir

    def compose(self) -> ComposeResult:
        if isinstance(self.card, SprintCard):
            sprint = self.card.sprint
            parent = sprint.movable_path.parent
            if parent.name.startswith("epic-"):
                label = f"Epic (via S-{sprint.number:02d})"
            else:
                label = f"S-{sprint.number:02d}"
        else:
            label = f"E-{self.card.epic.number:02d}"

        with Vertical(id="move-dialog"):
            yield Static(f"[bold]Move {label} to:[/]", id="move-title")
            options = []
            for col in self.all_columns:
                if col.name == self.current_col:
                    options.append(Option(f"{col.display_name} [dim](current)[/]", id=col.name, disabled=True))
                else:
                    options.append(Option(col.display_name, id=col.name))
            yield OptionList(*options, id="move-options")

    @on(OptionList.OptionSelected, "#move-options")
    def _on_option_selected(self, event: OptionList.OptionSelected) -> None:
        target_col = event.option.id
        if target_col is None or target_col == self.current_col:
            return
        target_dir = self.kanban_dir / target_col

        if isinstance(self.card, EpicCard):
            # Move entire epic folder (sprints stay inside)
            src = self.card.epic.path
            shutil.move(str(src), str(target_dir / src.name))
        elif isinstance(self.card, SprintCard):
            sprint = self.card.sprint
            # If sprint is inside an epic folder, move the whole epic
            parent = sprint.movable_path.parent
            if parent.name.startswith("epic-"):
                shutil.move(str(parent), str(target_dir / parent.name))
                # Record history for the moved sprint
                new_md = target_dir / parent.name / sprint.movable_path.name / sprint.path.name
                if not new_md.exists():
                    new_md = target_dir / parent.name / sprint.path.relative_to(parent)
                if new_md.exists():
                    write_history_entry(new_md, target_col)
            else:
                # Standalone sprint — move just the sprint
                src = sprint.movable_path
                shutil.move(str(src), str(target_dir / src.name))
                # Record history for the moved sprint
                if sprint.is_folder:
                    new_md = target_dir / src.name / sprint.path.name
                else:
                    new_md = target_dir / src.name
                if new_md.exists():
                    write_history_entry(new_md, target_col)

        self.dismiss(target_col)

    def action_cancel(self) -> None:
        self.dismiss(None)


class RejectModal(ModalScreen[str | None]):
    CSS = """
    RejectModal { align: center middle; }
    #reject-dialog {
        width: 50; height: auto; max-height: 12;
        border: solid $error; background: $surface; padding: 1 2;
    }
    #reject-title { text-align: center; padding-bottom: 1; }
    #reject-input { width: 100%; }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, sprint_number: int) -> None:
        super().__init__()
        self.sprint_number = sprint_number

    def compose(self) -> ComposeResult:
        with Vertical(id="reject-dialog"):
            yield Static(f"[bold red]Reject S-{self.sprint_number:02d}[/]", id="reject-title")
            yield Static("Rejection reason:")
            yield Input(placeholder="Why is this being rejected?", id="reject-input")

    @on(Input.Submitted, "#reject-input")
    def _on_submit(self, event: Input.Submitted) -> None:
        reason = event.value.strip()
        if reason:
            self.dismiss(reason)

    def action_cancel(self) -> None:
        self.dismiss(None)


MAIN_COLUMNS = {"1-todo", "2-in-progress", "3-review", "4-done"}


class KanbanApp(App):
    TITLE = "Kanban Board"

    CSS = """
    #main-layout {
        height: 1fr;
        width: 100%;
    }

    #board {
        width: 1fr;
        height: 100%;
    }

    KanbanColumn {
        width: 1fr;
        height: 100%;
        border-right: solid $surface-lighten-2;
        padding: 0;
    }

    KanbanColumn.hidden-col {
        display: none;
    }

    KanbanColumn.active-col {
        border-right: solid $accent;
        border-left: solid $accent;
    }

    .column-header {
        text-align: center;
        padding: 0;
        background: $surface-lighten-1;
        margin-bottom: 1;
        height: 1;
    }

    .empty-label {
        text-align: center;
        color: $text-muted;
    }

    .card {
        padding: 0 1;
        margin: 0;
    }

    .card:focus-within {
        background: $surface-lighten-1;
    }

    .card:focus {
        background: $surface-lighten-1;
    }

    .nested-sprint {
        margin-left: 1;
        padding: 0 0;
    }

    .nested-sprint.collapsed {
        display: none;
    }

    .nested-sprint:focus {
        background: $surface-lighten-2;
    }

    SprintCard:focus {
        background: $surface-lighten-1;
    }

    EpicCard:focus {
        background: $surface-lighten-1;
    }

    #detail-panel {
        width: 50;
        height: 100%;
        border-left: solid $primary;
        padding: 1 1;
        display: none;
    }

    #detail-panel.visible {
        display: block;
    }

    #detail-content {
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "start_sprint", "Start"),
        Binding("m", "move_card", "Move"),
        Binding("c", "complete_review", "Complete"),
        Binding("x", "reject_review", "Reject"),
        Binding("d", "toggle_detail", "Detail"),
        Binding("a", "toggle_all_cols", "All Cols"),
        Binding("left", "col_left", "< Col", show=True),
        Binding("right", "col_right", "Col >", show=True),
        Binding("up", "card_up", "", show=False),
        Binding("down", "card_down", "", show=False),
        Binding("enter", "toggle_expand", "Expand"),
        Binding("question_mark", "help_screen", "?=Help"),
    ]

    def __init__(self, kanban_dir: Path | None = None) -> None:
        super().__init__()
        self.kanban_dir = kanban_dir or self._find_kanban_dir()
        self.columns: list[ColumnInfo] = []
        self.active_col_index: int = 0
        self.show_all_columns: bool = False

    def _find_kanban_dir(self) -> Path:
        candidates = [Path.cwd() / "kanban", Path(__file__).parent.parent / "kanban"]
        for c in candidates:
            if c.is_dir():
                return c
        return Path.cwd() / "kanban"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with Horizontal(id="board"):
                self.columns = scan_kanban(self.kanban_dir)
                for i, col in enumerate(self.columns):
                    yield KanbanColumn(col, col_index=i, id=f"col-{col.name}")
            yield DetailPanel(id="detail-panel")
        yield Footer()

    def on_mount(self) -> None:
        self._apply_column_visibility()
        self._highlight_active_column()

    @on(CardSelected)
    def _on_card_selected(self, event: CardSelected) -> None:
        panel = self.query_one("#detail-panel", DetailPanel)
        panel.title_text = event.title
        panel.content_text = event.markdown_content

    @on(EpicExpandToggled)
    def _on_epic_expand_toggled(self, event: EpicExpandToggled) -> None:
        """Sync expand/collapse state across all columns for the same epic."""
        for card in self.query(EpicCard):
            if card.epic.number == event.epic_number and card.expanded != event.expanded:
                card.expanded = event.expanded

    # -- Column visibility --

    def _apply_column_visibility(self) -> None:
        cols = self._get_column_widgets()
        for col in cols:
            is_secondary = col.column.name not in MAIN_COLUMNS
            col.set_class(is_secondary and not self.show_all_columns, "hidden-col")
        # If active column is now hidden, jump to first visible
        visible = self._get_visible_col_indices()
        if visible and self.active_col_index not in visible:
            self.active_col_index = visible[0]

    def _get_visible_col_indices(self) -> list[int]:
        cols = self._get_column_widgets()
        return [i for i, c in enumerate(cols) if not c.has_class("hidden-col")]

    def action_toggle_all_cols(self) -> None:
        self.show_all_columns = not self.show_all_columns
        self._apply_column_visibility()
        self._highlight_active_column()
        label = "all" if self.show_all_columns else "main"
        self.notify(f"Showing {label} columns")

    # -- Column navigation --

    def _get_column_widgets(self) -> list[KanbanColumn]:
        return list(self.query("KanbanColumn"))

    def _highlight_active_column(self) -> None:
        cols = self._get_column_widgets()
        for i, col in enumerate(cols):
            col.set_class(i == self.active_col_index, "active-col")

    def _focusable_cards_in_column(self, col_index: int) -> list[SprintCard | EpicCard]:
        cols = self._get_column_widgets()
        if col_index < 0 or col_index >= len(cols):
            return []
        col_widget = cols[col_index]
        cards: list[SprintCard | EpicCard] = []
        for w in col_widget.walk_children():
            if isinstance(w, (SprintCard, EpicCard)) and w.can_focus:
                # Skip collapsed nested sprints
                if w.has_class("collapsed"):
                    continue
                cards.append(w)
        return cards

    def action_col_left(self) -> None:
        visible = self._get_visible_col_indices()
        if not visible:
            return
        try:
            pos = visible.index(self.active_col_index)
            if pos > 0:
                self.active_col_index = visible[pos - 1]
                self._highlight_active_column()
                self._focus_first_in_active_col()
        except ValueError:
            self.active_col_index = visible[0]
            self._highlight_active_column()
            self._focus_first_in_active_col()

    def action_col_right(self) -> None:
        visible = self._get_visible_col_indices()
        if not visible:
            return
        try:
            pos = visible.index(self.active_col_index)
            if pos < len(visible) - 1:
                self.active_col_index = visible[pos + 1]
                self._highlight_active_column()
                self._focus_first_in_active_col()
        except ValueError:
            self.active_col_index = visible[0]
            self._highlight_active_column()
            self._focus_first_in_active_col()

    def _focus_first_in_active_col(self) -> None:
        cards = self._focusable_cards_in_column(self.active_col_index)
        if cards:
            cards[0].focus()
        else:
            cols = self._get_column_widgets()
            if self.active_col_index < len(cols):
                cols[self.active_col_index].focus()

    def action_card_up(self) -> None:
        cards = self._focusable_cards_in_column(self.active_col_index)
        if not cards:
            return
        focused = self.focused
        try:
            idx = cards.index(focused)
            if idx > 0:
                cards[idx - 1].focus()
        except ValueError:
            cards[-1].focus()

    def action_card_down(self) -> None:
        cards = self._focusable_cards_in_column(self.active_col_index)
        if not cards:
            return
        focused = self.focused
        try:
            idx = cards.index(focused)
            if idx < len(cards) - 1:
                cards[idx + 1].focus()
        except ValueError:
            cards[0].focus()

    # -- Keep active_col_index in sync when user tabs into a card --

    def watch_focused(self, focused) -> None:
        if isinstance(focused, (SprintCard, EpicCard)):
            if hasattr(focused, "col_index"):
                self.active_col_index = focused.col_index
                self._highlight_active_column()

    # -- Refresh --

    async def action_refresh(self) -> None:
        board = self.query_one("#board", Horizontal)
        for child in list(board.children):
            await child.remove()

        self.columns = scan_kanban(self.kanban_dir)
        for i, col in enumerate(self.columns):
            await board.mount(KanbanColumn(col, col_index=i, id=f"col-{col.name}"))
        self._apply_column_visibility()
        self._highlight_active_column()
        self.notify("Board refreshed")

    # -- Move --

    def _get_focused_card_info(self) -> tuple[SprintCard | EpicCard | None, str | None]:
        focused = self.focused
        if isinstance(focused, SprintCard):
            return focused, focused.column_name
        if isinstance(focused, EpicCard):
            return focused, focused.column_name
        return None, None

    def action_move_card(self) -> None:
        card, current_col = self._get_focused_card_info()
        if card is None:
            self.notify("Select a card first", severity="warning")
            return

        def _on_move_result(result: str | None) -> None:
            if result:
                self.run_worker(self.action_refresh())

        self.push_screen(MoveScreen(card, current_col, self.columns, self.kanban_dir), callback=_on_move_result)

    # -- Sprint actions (start / complete / reject) --

    def _is_in_todo_column(self) -> bool:
        """Check if the focused card is in the todo column."""
        card, col = self._get_focused_card_info()
        return card is not None and col == "1-todo"

    def _is_in_review_column(self) -> bool:
        """Check if the focused card is in the review column."""
        card, col = self._get_focused_card_info()
        return card is not None and col == "3-review"

    def _get_sprint_id(self, sprint: SprintInfo) -> str:
        """Derive sprint ID for the execution engine from sprint info."""
        return f"sprint-{sprint.number}"

    async def action_start_sprint(self) -> None:
        """Start a sprint: move to In Progress and run execution in background."""
        if not self._is_in_todo_column():
            self.notify("Start is only available for sprints in the Todo column", severity="warning")
            return
        card, _ = self._get_focused_card_info()
        if not isinstance(card, SprintCard):
            self.notify("Select a sprint card to start", severity="warning")
            return

        sprint = card.sprint

        # Step 1: Move card to in-progress immediately
        try:
            from src.adapters.kanban import KanbanAdapter

            backend = KanbanAdapter(self.kanban_dir)
            sprint_id = self._get_sprint_id(sprint)
            await backend.start_sprint(sprint_id)
        except Exception:
            # Fallback to filesystem move
            write_history_entry(sprint.path, "2-in-progress")
            src = sprint.movable_path
            parent = src.parent
            target = self.kanban_dir / "2-in-progress"
            target.mkdir(parents=True, exist_ok=True)
            if parent.name.startswith("epic-"):
                shutil.move(str(parent), str(target / parent.name))
            else:
                shutil.move(str(src), str(target / src.name))

        await self.action_refresh()
        self.notify(f"S-{sprint.number:02d} started — running execution engine...")

        # Step 2: Run execution engine in background worker (non-blocking)
        sprint_num = sprint.number
        kanban_dir = self.kanban_dir

        async def _run_engine() -> None:
            from src.adapters.kanban import KanbanAdapter
            from src.execution.convenience import run_sprint

            be = KanbanAdapter(kanban_dir)
            sid = f"sprint-{sprint_num}"
            result = await run_sprint(sid, backend=be, kanban_dir=kanban_dir)

            if result.success:
                if result.stopped_at_review:
                    self.notify(
                        f"S-{sprint_num:02d} ready for review! "
                        f"({len(result.phase_results)} phases complete)",
                        severity="information",
                    )
                else:
                    self.notify(f"S-{sprint_num:02d} completed!", severity="information")
            else:
                phase = result.current_phase.value.upper() if result.current_phase else "unknown"
                self.notify(f"S-{sprint_num:02d} blocked at {phase}", severity="error")

            self.run_worker(self.action_refresh())

        self.run_worker(_run_engine())

    async def action_complete_review(self) -> None:
        if not self._is_in_review_column():
            self.notify("Complete is only available for cards in the Review column", severity="warning")
            return
        card, _ = self._get_focused_card_info()
        if not isinstance(card, SprintCard):
            self.notify("Select a sprint card to complete", severity="warning")
            return

        sprint = card.sprint

        try:
            from src.adapters.kanban import KanbanAdapter

            backend = KanbanAdapter(self.kanban_dir)
            sprint_id = self._get_sprint_id(sprint)
            await backend.complete_sprint(sprint_id)
            self.notify(f"S-{sprint.number:02d} completed!", severity="information")
        except Exception:
            # Fallback to filesystem operations if adapter fails
            write_history_entry(sprint.path, "4-done")
            src = sprint.movable_path
            target = self.kanban_dir / "4-done"
            target.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(target / src.name))
            self.notify(f"S-{sprint.number:02d} completed!", severity="information")

        await self.action_refresh()


    def action_reject_review(self) -> None:
        if not self._is_in_review_column():
            self.notify("Reject is only available for cards in the Review column", severity="warning")
            return
        card, _ = self._get_focused_card_info()
        if not isinstance(card, SprintCard):
            self.notify("Select a sprint card to reject", severity="warning")
            return

        sprint = card.sprint

        def _on_reject_result(reason: str | None) -> None:
            if reason is None:
                return

            try:
                import asyncio

                from src.adapters.kanban import KanbanAdapter

                backend = KanbanAdapter(self.kanban_dir)
                sprint_id = self._get_sprint_id(sprint)
                asyncio.get_event_loop().create_task(backend.reject_sprint(sprint_id, reason))
            except Exception:
                # Fallback to filesystem operations
                write_history_entry(sprint.path, "2-in-progress")
                src = sprint.movable_path
                parent = src.parent
                target = self.kanban_dir / "2-in-progress"
                target.mkdir(parents=True, exist_ok=True)
                if parent.name.startswith("epic-"):
                    shutil.move(str(parent), str(target / parent.name))
                else:
                    shutil.move(str(src), str(target / src.name))

            self.notify(f"S-{sprint.number:02d} rejected: {reason}", severity="warning")
            self.run_worker(self.action_refresh())

        self.push_screen(RejectModal(sprint.number), callback=_on_reject_result)

    # -- Expand/collapse --

    def action_toggle_expand(self) -> None:
        focused = self.focused
        if isinstance(focused, EpicCard):
            focused.toggle_expanded()
        elif isinstance(focused, SprintCard):
            # If it's a nested sprint, toggle its parent epic
            parent = focused.parent
            while parent is not None:
                if isinstance(parent, EpicCard):
                    parent.toggle_expanded()
                    parent.focus()
                    break
                parent = parent.parent

    # -- Detail toggle --

    def action_toggle_detail(self) -> None:
        panel = self.query_one("#detail-panel", DetailPanel)
        panel.toggle_class("visible")

    def action_help_screen(self) -> None:
        self.notify(
            "[bold]Keys:[/] s=start  c=complete  x=reject  m=move  Left/Right=cols  Up/Down=cards  Enter=expand  d=detail  a=all cols  r=refresh  q=quit",
            timeout=6,
        )


def run_board() -> None:
    """Entry point for maestro-board CLI."""
    app = KanbanApp()
    app.run()
