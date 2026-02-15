"""agent-42 — minimal autonomous coding agent."""

import warnings
warnings.filterwarnings("ignore", message="Core Pydantic V1")

import json
import sys

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from config import PROVIDERS
from prompts import SYSTEM_PROMPT
from llm import make_llm, stream_response
from tools import execute_tool
from context import is_overflow, compact, prune, get_token_count
from ui import welcome, goodbye, get_user_input, show_chunk, show_response_end, show_tool_call, show_info, choose_provider


def main():
    provider = choose_provider(PROVIDERS)
    llm_base, llm = make_llm(provider)
    context_limit = provider.get("context_limit", 128_000)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    last_token_count = None
    welcome()

    while True:
        try:
            user_input = get_user_input()
        except (KeyboardInterrupt, EOFError):
            goodbye()

        if not user_input.strip():
            continue

        messages.append(HumanMessage(content=user_input))

        while True:
            if is_overflow(last_token_count, messages, context_limit):
                show_info("[auto-compact] Context approaching limit. Summarizing conversation...")
                messages, status = compact(llm_base, messages)
                if status == "ok":
                    show_info("[auto-compact] Done. Continuing with summarized context.\n")
                else:
                    show_info(f"[auto-compact] {status}. Keeping original conversation.\n")
                last_token_count = None

            response = stream_response(llm, messages, on_chunk=show_chunk)
            messages.append(response)

            last_token_count = get_token_count(response)

            if not response.tool_calls:
                show_response_end()
                break

            for tc in response.tool_calls:
                show_tool_call(tc["name"], tc["args"])
                result = execute_tool(tc["name"], tc["args"])
                messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

        messages, pruned = prune(messages)
        if pruned:
            show_info(f"[prune] Cleared {pruned} old tool outputs.")


if __name__ == "__main__":
    main()
