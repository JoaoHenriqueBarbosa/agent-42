"""Definições, implementações e dispatcher de tools."""

import os
import subprocess

from prompts import BASE_DIR

WORKSPACE = os.path.join(BASE_DIR, "workspace")
CONTAINER = "agent-42-sandbox"
BASH_TIMEOUT = 30

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
