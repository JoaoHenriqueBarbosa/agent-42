"""Interface de usuário — Textual TUI widgets."""

import json

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Markdown, Static, TextArea
from textual.binding import Binding


# ── Spinner (shared timer, inspired by claudechic/widgets/primitives/spinner.py) ──

class Spinner(Static):
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    _instances: set["Spinner"] = set()
    _frame: int = 0
    _timer = None

    DEFAULT_CSS = "Spinner { height: auto; width: auto; }"

    def on_mount(self) -> None:
        Spinner._instances.add(self)
        if Spinner._timer is None:
            Spinner._timer = self.app.set_interval(1 / 10, Spinner._tick_all)

    def on_unmount(self) -> None:
        Spinner._instances.discard(self)
        if not Spinner._instances and Spinner._timer is not None:
            Spinner._timer.stop()
            Spinner._timer = None

    @staticmethod
    def _tick_all() -> None:
        Spinner._frame = (Spinner._frame + 1) % len(Spinner.FRAMES)
        char = Spinner.FRAMES[Spinner._frame]
        for spinner in list(Spinner._instances):
            spinner.update(f"{char} {spinner._label}")

    def __init__(self, label: str = "Thinking...", **kwargs):
        super().__init__(f"⠋ {label}", **kwargs)
        self._label = label


# ── ThinkingIndicator ──

class ThinkingIndicator(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spinner = None

    def compose(self) -> ComposeResult:
        self._spinner = Spinner("Thinking...")
        yield self._spinner


# ── ChatMessage (markdown rendering + streaming) ──

class ChatMessage(Static):
    _DEBOUNCE_INTERVAL = 0.05
    _DEBOUNCE_MAX_CHARS = 200

    DEFAULT_CSS = "ChatMessage { height: auto; width: 1fr; }"

    def __init__(self, content: str = "", role: str = "assistant", **kwargs):
        super().__init__(**kwargs)
        self._content = content
        self._role = role
        self._pending_text = ""
        self._flush_timer = None
        self._md_widget: Markdown | None = None

    def compose(self) -> ComposeResult:
        self._md_widget = Markdown(self._content, id="content")
        yield self._md_widget

    def on_mount(self) -> None:
        if self._role == "user":
            self.add_class("user-message")
        else:
            self.add_class("assistant-message")

    def append_content(self, text: str) -> None:
        self._pending_text += text
        if len(self._pending_text) >= self._DEBOUNCE_MAX_CHARS:
            self._flush_pending()
        elif self._flush_timer is None:
            self._flush_timer = self.set_timer(
                self._DEBOUNCE_INTERVAL, self._flush_pending
            )

    def _flush_pending(self) -> None:
        if self._flush_timer is not None:
            self._flush_timer.stop()
            self._flush_timer = None
        if not self._pending_text:
            return
        self._content += self._pending_text
        self._pending_text = ""
        if self._md_widget:
            self._md_widget.update(self._content)

    def finalize(self) -> None:
        self._flush_pending()


# ── ToolWidget (collapsible tool call display) ──

class ToolWidget(Widget):
    DEFAULT_CSS = "ToolWidget { height: auto; width: 1fr; }"

    def __init__(self, name: str, args: dict, **kwargs):
        super().__init__(**kwargs)
        self._tool_name = name
        self._tool_args = args
        self._result: str | None = None
        self._header_widget: Static | None = None
        self._body_widget: Static | None = None
        self._spinner: Spinner | None = None

    def compose(self) -> ComposeResult:
        header_text = self._format_header()
        self._header_widget = Static(header_text, classes="tool-header")
        yield self._header_widget
        self._spinner = Spinner("running...")
        yield self._spinner
        self._body_widget = Static("", classes="tool-body-text")
        yield self._body_widget

    def on_mount(self) -> None:
        self.add_class("pending")

    def _format_header(self) -> str:
        match self._tool_name:
            case "bash":
                cmd = self._tool_args.get("command", "")
                short = cmd[:80] + ("..." if len(cmd) > 80 else "")
                return f"Bash: {short}"
            case "read_file":
                path = self._tool_args.get("path", "")
                return f"Read: {path}"
            case "write_file":
                path = self._tool_args.get("path", "")
                return f"Write: {path}"
            case _:
                return f"{self._tool_name}: {json.dumps(self._tool_args, ensure_ascii=False)[:80]}"

    def set_result(self, result: str) -> None:
        self._result = result
        self.remove_class("pending")

        if self._spinner:
            self._spinner.remove()
            self._spinner = None

        if not result or result == "(no output)":
            summary = "(no output)"
        else:
            lines = result.count("\n") + 1
            summary = f"({lines} lines)" if lines > 1 else f"({len(result)} chars)"

        if "Error" in result[:50]:
            self.add_class("error")
            summary = "(error)"
        else:
            self.add_class("completed")

        if self._header_widget:
            self._header_widget.update(f"{self._format_header()} {summary}")

        truncated = result[:2000] + ("\n..." if len(result) > 2000 else "")
        if self._body_widget:
            self._body_widget.update(truncated)

    def on_click(self) -> None:
        if self._result is not None:
            self.toggle_class("expanded")


# ── ChatInput (TextArea with submit/history) ──

class ChatInput(TextArea):

    class Submitted(Message):
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    BINDINGS = [
        Binding("up", "history_prev", "History prev", show=False),
        Binding("down", "history_next", "History next", show=False),
    ]

    DEFAULT_CSS = """
    ChatInput {
        height: auto;
        min-height: 1;
        max-height: 10;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(language=None, **kwargs)
        self._history: list[str] = []
        self._history_index: int = -1
        self._draft: str = ""

    def action_submit(self) -> None:
        text = self.text.strip()
        if not text:
            return
        self._history.append(text)
        self._history_index = -1
        self._draft = ""
        self.post_message(self.Submitted(text))
        self.clear()

    def _on_key(self, event) -> None:
        if event.key == "enter":
            event.prevent_default()
            self.action_submit()
            return
        if event.key == "shift+enter":
            event.prevent_default()
            self.insert("\n")
            return
        super()._on_key(event)

    def action_history_prev(self) -> None:
        if not self._history:
            return
        if self.cursor_location[0] > 0:
            self.action_cursor_up()
            return
        if self._history_index == -1:
            self._draft = self.text
            self._history_index = len(self._history) - 1
        elif self._history_index > 0:
            self._history_index -= 1
        else:
            return
        self.load_text(self._history[self._history_index])

    def action_history_next(self) -> None:
        if self._history_index == -1:
            return
        row_count = self.document.line_count
        if self.cursor_location[0] < row_count - 1:
            self.action_cursor_down()
            return
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.load_text(self._history[self._history_index])
        else:
            self._history_index = -1
            self.load_text(self._draft)


# ── ChatView (scrollable message container) ──

class ChatView(VerticalScroll):
    DEFAULT_CSS = "ChatView { height: 1fr; }"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_message: ChatMessage | None = None
        self._thinking: ThinkingIndicator | None = None
        self._tailing = True

    def on_scroll_up(self) -> None:
        self._tailing = self.scroll_offset.y >= (self.virtual_size.height - self.size.height - 2)

    def _auto_scroll(self) -> None:
        if self._tailing:
            self.scroll_end(animate=False)

    async def add_user_message(self, text: str) -> None:
        msg = ChatMessage(text, role="user")
        await self.mount(msg)
        self._auto_scroll()

    async def start_thinking(self) -> None:
        self._thinking = ThinkingIndicator()
        await self.mount(self._thinking)
        self._auto_scroll()

    async def stop_thinking(self) -> None:
        if self._thinking:
            await self._thinking.remove()
            self._thinking = None

    async def start_response(self) -> None:
        await self.stop_thinking()
        self._current_message = ChatMessage("", role="assistant")
        await self.mount(self._current_message)
        self._tailing = True

    def append_text(self, text: str) -> None:
        if self._current_message is None:
            return
        self._current_message.append_content(text)
        self._auto_scroll()

    def end_response(self) -> None:
        if self._current_message:
            self._current_message.finalize()
            self._current_message = None

    async def add_tool_call(self, name: str, args: dict, widget_id: str) -> "ToolWidget":
        await self.stop_thinking()
        tw = ToolWidget(name, args, id=widget_id)
        await self.mount(tw)
        self._auto_scroll()
        return tw

    async def add_info(self, text: str) -> None:
        info = Static(f"[dim]{text}[/dim]", markup=True)
        info.styles.height = "auto"
        info.styles.padding = (0, 1)
        info.styles.margin = (0, 0, 1, 0)
        await self.mount(info)
        self._auto_scroll()


# ── StatusFooter ──

class StatusFooter(Static):
    provider_name = reactive("")
    model_name = reactive("")
    status = reactive("idle")

    DEFAULT_CSS = """
    StatusFooter {
        height: 1;
        dock: bottom;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def render(self) -> str:
        status_icon = "..." if self.status == "thinking" else ""
        parts = []
        if self.provider_name:
            parts.append(self.provider_name)
        if self.model_name:
            parts.append(self.model_name)
        if status_icon:
            parts.append(status_icon)
        return " | ".join(parts) if parts else "agent-42"
