"""agent-42 — Textual TUI entrypoint."""

import warnings
warnings.filterwarnings("ignore", message="Core Pydantic V1")

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Button, Label, Static

from langchain_core.messages import HumanMessage, SystemMessage

from config import PROVIDERS
from prompts import SYSTEM_PROMPT
from llm import make_llm
from agent import run_turn
from ui import ChatView, ChatInput, StatusFooter


class Agent42App(App):
    TITLE = "agent-42"
    CSS_PATH = Path(__file__).parent / "styles.tcss"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True, show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._llm = None
        self._llm_base = None
        self._messages = []
        self._context_limit = 128_000
        self._last_token_count = None
        self._provider_name = ""
        self._model_name = ""
        self._tool_widgets = {}

    def compose(self) -> ComposeResult:
        yield ChatView(id="chat-view")
        with Container(id="input-container"):
            yield ChatInput(id="input")
        yield StatusFooter(id="footer")
        # Provider picker overlay
        with Container(id="provider-picker"):
            with Vertical(id="provider-picker-box"):
                yield Label("Select Provider")
                for name in PROVIDERS:
                    yield Button(name, id=f"provider-{name}")

    def on_mount(self) -> None:
        self.query_one("#input").display = False
        self.query_one("#chat-view").display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("provider-"):
            provider_key = event.button.id.removeprefix("provider-")
            self._select_provider(provider_key)

    def _select_provider(self, provider_key: str) -> None:
        provider = PROVIDERS[provider_key]
        self._llm_base, self._llm = make_llm(provider)
        self._context_limit = provider.get("context_limit", 128_000)
        self._messages = [SystemMessage(content=SYSTEM_PROMPT)]
        self._last_token_count = None
        self._provider_name = provider_key
        self._model_name = provider.get("model", "")

        # Hide picker, show chat
        self.query_one("#provider-picker").display = False
        self.query_one("#input").display = True
        self.query_one("#chat-view").display = True

        footer = self.query_one("#footer", StatusFooter)
        footer.provider_name = self._provider_name
        footer.model_name = self._model_name

        self.query_one("#input", ChatInput).focus()

    async def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        await chat_view.add_user_message(event.value)
        self._messages.append(HumanMessage(content=event.value))

        footer = self.query_one("#footer", StatusFooter)
        footer.status = "thinking"

        self.query_one("#input", ChatInput).disabled = True
        self._tool_widgets = {}

        self.run_worker(self._run_agent_turn(), exclusive=True)

    async def _run_agent_turn(self) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        _first_chunk = True

        async def on_response_start():
            nonlocal _first_chunk
            _first_chunk = True
            await chat_view.start_thinking()

        async def on_chunk(text):
            nonlocal _first_chunk
            if _first_chunk:
                await chat_view.start_response()
                _first_chunk = False
            chat_view.append_text(text)

        async def on_tool_call(name, args, tc_id):
            nonlocal _first_chunk
            if not _first_chunk:
                chat_view.end_response()
                _first_chunk = True
            tw = await chat_view.add_tool_call(name, args, widget_id=f"tool-{tc_id}")
            self._tool_widgets[tc_id] = tw

        async def on_tool_result(tc_id, result):
            tw = self._tool_widgets.get(tc_id)
            if tw:
                tw.set_result(result)

        async def on_info(message):
            await chat_view.add_info(message)

        async def on_response_end():
            chat_view.end_response()

        callbacks = {
            "on_chunk": on_chunk,
            "on_tool_call": on_tool_call,
            "on_tool_result": on_tool_result,
            "on_info": on_info,
            "on_response_start": on_response_start,
            "on_response_end": on_response_end,
        }

        try:
            self._messages, self._last_token_count = await run_turn(
                self._llm, self._llm_base, self._messages,
                self._context_limit, self._last_token_count, callbacks,
            )
        except Exception as e:
            await chat_view.add_info(f"[error] {e}")

        footer = self.query_one("#footer", StatusFooter)
        footer.status = "idle"

        input_widget = self.query_one("#input", ChatInput)
        input_widget.disabled = False
        input_widget.focus()


if __name__ == "__main__":
    Agent42App().run()
