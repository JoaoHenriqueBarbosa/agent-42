"""Factory do LLM e streaming."""

from langchain_openai import ChatOpenAI

from tools import TOOLS


def make_llm(provider):
    base = ChatOpenAI(
        model=provider["model"],
        api_key=provider["api_key"],
        base_url=provider["base_url"],
        stream_usage=True,
    )
    return base, base.bind_tools(TOOLS)


def stream_response(llm, messages, on_chunk=None):
    """Streama a resposta e retorna a mensagem completa."""
    full = None
    for chunk in llm.stream(messages):
        if full is None:
            full = chunk
        else:
            full = full + chunk
        if chunk.content and on_chunk:
            on_chunk(chunk.content)
    return full


async def astream_response(llm, messages, on_chunk=None):
    """Versão async de stream_response usando astream."""
    full = None
    async for chunk in llm.astream(messages):
        if full is None:
            full = chunk
        else:
            full = full + chunk
        if chunk.content and on_chunk:
            await on_chunk(chunk.content)
    return full
