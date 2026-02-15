"""ClaudeAgent MVP — o loop mais simples possível."""

import warnings
warnings.filterwarnings("ignore", message="Core Pydantic V1")

import json
import os
import subprocess
import sys

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from config import PROVIDERS

BASE_DIR = os.path.dirname(__file__)
WORKSPACE = os.path.join(BASE_DIR, "workspace")
CONTAINER = "agent-42-sandbox"
BASH_TIMEOUT = 30

with open(os.path.join(BASE_DIR, "system_prompt.txt")) as f:
    SYSTEM_PROMPT = f.read()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute a bash command. The working directory is /workspace. Timeout: 30s.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to execute"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the workspace. Returns content with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path within the workspace"},
                    "start_line": {"type": "integer", "description": "First line (1-indexed)"},
                    "end_line": {"type": "integer", "description": "Last line (1-indexed)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path within the workspace"},
                    "content": {"type": "string", "description": "Full content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
]


# --- Tools ---

def execute_tool(name, args):
    match name:
        case "bash":
            return tool_bash(**args)
        case "read_file":
            return tool_read_file(**args)
        case "write_file":
            return tool_write_file(**args)
        case _:
            return f"Unknown tool: {name}"

def tool_bash(command):
    try:
        result = subprocess.run(
            ["docker", "exec", CONTAINER, "bash", "-c", command],
            capture_output=True, text=True, timeout=BASH_TIMEOUT,
        )
        output = result.stdout + result.stderr
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {BASH_TIMEOUT}s"
    except Exception as e:
        return f"Error: {e}"

def _safe_path(path):
    full = os.path.join(WORKSPACE, path)
    if not os.path.abspath(full).startswith(os.path.abspath(WORKSPACE)):
        return None
    return full

def tool_read_file(path, start_line=None, end_line=None):
    full_path = _safe_path(path)
    if not full_path:
        return "Error: path outside workspace"
    try:
        with open(full_path) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error: {e}"

    start = (start_line or 1) - 1
    end = end_line or len(lines)
    numbered = [f"{i:4d} | {l.rstrip()}" for i, l in enumerate(lines[start:end], start=start + 1)]
    return "\n".join(numbered)

def tool_write_file(path, content):
    full_path = _safe_path(path)
    if not full_path:
        return "Error: path outside workspace"
    try:
        parent = os.path.dirname(full_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        return f"OK: wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


# --- LLM ---

def make_llm(provider):
    return ChatOpenAI(
        model=provider["model"],
        api_key=provider["api_key"],
        base_url=provider["base_url"],
    ).bind_tools(TOOLS)

def choose_provider():
    names = list(PROVIDERS)
    print("Provider:")
    for i, name in enumerate(names, 1):
        print(f"  {i}) {name}")
    while True:
        choice = input(f"Escolha [1-{len(names)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            selected = names[int(choice) - 1]
            print(f"→ {selected}\n")
            return PROVIDERS[selected]


# --- O Loop ---

def stream_response(llm, messages):
    """Streama a resposta e retorna a mensagem completa."""
    full = None
    for chunk in llm.stream(messages):
        if full is None:
            full = chunk
        else:
            full = full + chunk
        if chunk.content:
            print(chunk.content, end="", flush=True)
    return full

def main():
    llm = make_llm(choose_provider())
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    print("agent-42 (ctrl+c para sair)\n")

    while True:
        try:
            user_input = input("> ")
        except (KeyboardInterrupt, EOFError):
            print("\nbye")
            sys.exit(0)

        if not user_input.strip():
            continue

        messages.append(HumanMessage(content=user_input))

        # O loop do agente: chama a API, se vier tool_use executa e manda de volta.
        # Quando vier só texto, exibe e volta pro input do usuário.
        while True:
            response = stream_response(llm, messages)
            messages.append(response)

            if not response.tool_calls:
                print("\n")
                break

            for tc in response.tool_calls:
                print(f"\n[{tc['name']}] {json.dumps(tc['args'], ensure_ascii=False)}")
                result = execute_tool(tc["name"], tc["args"])
                messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

if __name__ == "__main__":
    main()
