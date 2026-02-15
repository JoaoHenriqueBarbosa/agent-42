"""agent-42 — minimal autonomous coding agent."""

import warnings
warnings.filterwarnings("ignore", message="Core Pydantic V1")

import asyncio
import json
import sys

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from config import PROVIDERS
from prompts import SYSTEM_PROMPT
from llm import make_llm, stream_response, astream_response
from tools import execute_tool
from context import is_overflow, compact, prune, get_token_count


async def run_turn(llm, llm_base, messages, context_limit, last_token_count, callbacks):
    """Processa um turno do agente (async).

    callbacks = dict com:
        on_chunk(text)        — async, chamado a cada chunk de texto
        on_tool_call(name, args, tc_id) — async, chamado ao iniciar tool
        on_tool_result(tc_id, result)   — async, chamado com resultado da tool
        on_info(message)      — async, mensagem informativa
        on_response_start()   — async, início de resposta do LLM
        on_response_end()     — async, fim de resposta (sem tool calls)
    """
    on_chunk = callbacks.get("on_chunk")
    on_tool_call = callbacks.get("on_tool_call")
    on_tool_result = callbacks.get("on_tool_result")
    on_info = callbacks.get("on_info")
    on_response_start = callbacks.get("on_response_start")
    on_response_end = callbacks.get("on_response_end")

    while True:
        if is_overflow(last_token_count, messages, context_limit):
            if on_info:
                await on_info("[auto-compact] Context approaching limit. Summarizing conversation...")
            messages, status = compact(llm_base, messages)
            if on_info:
                if status == "ok":
                    await on_info("[auto-compact] Done. Continuing with summarized context.\n")
                else:
                    await on_info(f"[auto-compact] {status}. Keeping original conversation.\n")
            last_token_count = None

        if on_response_start:
            await on_response_start()

        response = await astream_response(llm, messages, on_chunk=on_chunk)
        messages.append(response)

        last_token_count = get_token_count(response)

        if not response.tool_calls:
            if on_response_end:
                await on_response_end()
            break

        for tc in response.tool_calls:
            if on_tool_call:
                await on_tool_call(tc["name"], tc["args"], tc["id"])
            result = await asyncio.to_thread(execute_tool, tc["name"], tc["args"])
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
            if on_tool_result:
                await on_tool_result(tc["id"], result)

    messages, pruned = prune(messages)
    if pruned and on_info:
        await on_info(f"[prune] Cleared {pruned} old tool outputs.")

    return messages, last_token_count


# ── CLI fallback (mantém compatibilidade) ──

def main():
    from ui_cli import (
        welcome, goodbye, get_user_input, show_chunk,
        show_response_end, show_tool_call, show_info, choose_provider,
    )

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
