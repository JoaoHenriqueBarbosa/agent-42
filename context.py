"""Gerenciamento de contexto: token counting, overflow, pruning, compaction."""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from prompts import SYSTEM_PROMPT, COMPACT_PROMPT, COMPACT_SYSTEM

COMPACT_BUFFER = 20_000
CHARS_PER_TOKEN = 4
PRUNE_PROTECT = 40_000
PRUNE_MINIMUM = 20_000


def get_token_count(response):
    """Extract total token count from LLM response, or None if unavailable."""
    meta = getattr(response, "usage_metadata", None)
    if meta:
        input_t = meta.get("input_tokens", 0)
        output_t = meta.get("output_tokens", 0)
        if input_t > 0:
            return input_t + output_t
    resp_meta = getattr(response, "response_metadata", None)
    if resp_meta:
        usage = resp_meta.get("token_usage") or resp_meta.get("usage", {})
        if isinstance(usage, dict):
            prompt_t = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
            compl_t = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
            if prompt_t > 0:
                return prompt_t + compl_t
    return None


def estimate_tokens(messages):
    """Fallback: estimate total tokens using character heuristic (len/4)."""
    total_chars = 0
    for msg in messages:
        if isinstance(msg.content, str):
            total_chars += len(msg.content)
        elif isinstance(msg.content, list):
            for part in msg.content:
                total_chars += len(json.dumps(part)) if isinstance(part, dict) else len(str(part))
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            total_chars += len(json.dumps(msg.tool_calls, default=str))
    return total_chars // CHARS_PER_TOKEN


def is_overflow(token_count, messages, context_limit):
    """Check if conversation tokens are approaching the context limit."""
    if context_limit <= 0:
        return False
    count = token_count if token_count else estimate_tokens(messages)
    return count >= context_limit - COMPACT_BUFFER


def prune(messages):
    """Clear old tool outputs to reduce context size without full summarization.
    Returns (new_messages, pruned_count)."""
    user_count = 0
    cutoff = len(messages)
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            user_count += 1
            if user_count >= 2:
                cutoff = i
                break

    tool_indices = []
    for i in range(cutoff):
        if isinstance(messages[i], ToolMessage) and messages[i].content != "[output cleared]":
            est = len(messages[i].content) // CHARS_PER_TOKEN
            tool_indices.append((i, est))

    if not tool_indices:
        return messages, 0

    protected = 0
    pruneable = set()
    for idx, est in reversed(tool_indices):
        if protected < PRUNE_PROTECT:
            protected += est
        else:
            pruneable.add(idx)

    total_pruneable = sum(len(messages[i].content) // CHARS_PER_TOKEN for i in pruneable)
    if total_pruneable < PRUNE_MINIMUM:
        return messages, 0

    result = []
    for i, msg in enumerate(messages):
        if i in pruneable:
            result.append(ToolMessage(
                content="[output cleared]",
                tool_call_id=msg.tool_call_id,
            ))
        else:
            result.append(msg)
    return result, len(pruneable)


def compact(llm_base, messages):
    """Summarize the conversation and return a fresh message list.
    Returns (new_messages, status) where status is 'ok', 'failed', or error message."""
    try:
        compact_messages = [
            SystemMessage(content=COMPACT_SYSTEM),
            *messages[1:],
            HumanMessage(content=COMPACT_PROMPT),
        ]
        summary_response = llm_base.invoke(compact_messages)
        summary = summary_response.content
        return [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content="What did we do so far?"),
            AIMessage(content=summary),
            HumanMessage(
                content="Continue where you left off. If you have next steps, "
                "proceed. Otherwise, ask for clarification."
            ),
        ], "ok"
    except Exception as e:
        return messages, f"failed: {e}"
