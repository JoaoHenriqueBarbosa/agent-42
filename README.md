# agent-42

A minimal autonomous coding agent. No frameworks, no magic — just a while loop with tool use.

```
> Create a Flask API with a /health endpoint

[write_file] {"path": "app.py", "content": "from flask import Flask..."}
[bash] {"command": "pip install flask && python app.py &"}
[bash] {"command": "curl localhost:5000/health"}

Done. The API is running and /health returns {"status": "ok"}.
```

## Why

The secret of a good coding agent is the simplicity of the loop. The API responds with a tool call, streaming stops, the system executes the tool locally, and the result goes back as a new message. This synchronous, atomic cycle enables **interleaved thinking** — the model reasons again at each step with fresh context.

Any abstraction over this loop that obscures this mechanism is cost without benefit.

## How it works

```python
while True:
    response = llm.stream(messages)

    if response has tool_calls:
        result = execute_tool(tool_call)
        messages.append(tool_result(result))
        continue

    display(response.text)
    messages.append(user_input())
```

That's it. The intelligence is in the model, not in the code.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Terminal   │────▶│    agent.py      │────▶│   LLM Provider  │
│  (stdin/out) │◀────│  (~200 lines)    │◀────│  (any OpenAI-   │
└─────────────┘     │                  │     │   compatible)   │
                    │  tool dispatch:  │     └─────────────────┘
                    │  match/case      │
                    └──────┬───────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │   bash   │ │read_file │ │write_file│
        │ (docker) │ │ (host)   │ │ (host)   │
        └──────────┘ └──────────┘ └──────────┘
              │
              ▼
        ┌──────────────┐
        │   Docker     │
        │   sandbox    │
        │  (no network)│
        └──────────────┘
```

- **bash** runs inside a Docker container with no network access
- **read_file** and **write_file** operate on the host through a shared `workspace/` volume
- All providers go through a single `ChatOpenAI` — LangChain is used only as a provider adapter

## Tools

| Tool | Description |
|------|-------------|
| `bash` | Execute shell commands in an isolated Docker container. Timeout: 30s. |
| `read_file` | Read a file with line numbers. Supports `start_line`/`end_line` ranges. |
| `write_file` | Create or overwrite a file. Creates parent directories automatically. |

Tools are defined as plain Python dicts (OpenAI function calling format). No `@tool` decorators, no LangChain tooling abstractions. Execution is a `match/case` in the main loop.

## Providers

Any OpenAI-compatible API works. Preconfigured:

| Provider | Model | Endpoint |
|----------|-------|----------|
| Anthropic | claude-sonnet-4 | `api.anthropic.com/v1/` (OpenAI-compatible) |
| OpenAI | gpt-4o-mini | `api.openai.com/v1` |
| Z.AI | GLM-4.5-air | `api.z.ai/api/coding/paas/v4` |

Switch providers at startup — no code changes needed. Add your own by editing `config.py`.

## Setup

**Requirements:** Python 3.10+, Docker

```bash
# Clone
git clone https://github.com/JoaoHenriqueBarbosa/agent-42.git
cd agent-42

# Python dependencies
python -m venv venv
source venv/bin/activate
pip install langchain-openai python-dotenv

# Docker sandbox
docker compose up -d

# API keys
cp .env.example .env
# Edit .env with your keys
```

## Configuration

Create a `.env` file:

```env
# At least one provider is required

# Anthropic (via OpenAI-compatible endpoint)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_BASE_URL=https://api.anthropic.com/v1/
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# OpenAI
OPENAI_API_KEY=sk-proj-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Z.AI (or any OpenAI-compatible provider)
ZAI_API_KEY=your-key
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
ZAI_MODEL=GLM-4.5-air
```

## Run

```bash
venv/bin/python agent.py
```

```
Provider:
  1) anthropic
  2) zai
  3) openai
Escolha [1-3]: 1
→ anthropic

agent-42 (ctrl+c para sair)

> _
```

## Design decisions

**Why LangChain at all?** It solves exactly one problem: not having to maintain separate HTTP clients for different message formats. If LangChain dies tomorrow, the migration is replacing `.stream()` with direct HTTP calls. Nothing else changes.

**Why not more LangChain?** Chains, agents, memory modules, output parsers — none of that is used. The loop is too simple to benefit from abstraction. Our context management is specific to our case. Tool descriptions need precise control over the JSON schema the model receives.

**Why Docker for bash?** The model can run arbitrary shell commands. Docker with `network_mode: none` provides isolation without complexity. The model doesn't know it's in a container.

**Why `ChatOpenAI` for Anthropic?** Anthropic offers an [OpenAI-compatible endpoint](https://docs.anthropic.com/en/api/openai-sdk). Using a single `ChatOpenAI` class for all providers eliminates format differences (Anthropic returns content as a list of blocks, OpenAI as a string). Zero branching by provider in the entire codebase.

## What kind of agent is this?

agent-42 implements what is essentially a **native tool use agent loop** — the practical evolution of the [ReAct](https://arxiv.org/abs/2210.03629) pattern (Yao et al., 2022).

ReAct formalized the cycle of *reason → act → observe → reason again*, but at the time there was no native tool use in LLM APIs. The original approach forced the model to generate explicit tokens like `Thought:`, `Action:`, `Observation:` via prompting — a hack to simulate the loop.

With native tool use APIs, the pattern became infrastructure:

| ReAct concept | Native implementation |
|---|---|
| Thought | Extended thinking / internal reasoning |
| Action | `tool_use` block (typed, structured) |
| Observation | `tool_result` message back to the model |

agent-42 is this loop without any translation layer. The model speaks directly to the system. That's why it delivers more agency than most frameworks — there's no indirection obscuring the mechanism.

### References

1. **ReAct: Synergizing Reasoning and Acting in Language Models** — Yao et al., 2022. The original paper that formalized the reason-act-observe pattern. [arXiv:2210.03629](https://arxiv.org/abs/2210.03629)
2. **Toolformer: Language Models Can Teach Themselves to Use Tools** — Schick et al., 2023. Shows that models learn to use tools in an emergent way. [arXiv:2302.04761](https://arxiv.org/abs/2302.04761)
3. **Tool Use — Anthropic Documentation.** Documents the native tool use pattern that replaced ReAct-style prompting. [docs.anthropic.com](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
4. **Function Calling — OpenAI Documentation.** OpenAI's equivalent implementation. [platform.openai.com](https://platform.openai.com/docs/guides/function-calling)

## Roadmap

- [ ] Context compaction (summarize conversation when approaching token limit)
- [ ] Ctrl+C to cancel running tools
- [ ] Session persistence to disk
- [ ] System prompt refinement

## License

MIT
