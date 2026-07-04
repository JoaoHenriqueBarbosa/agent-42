# Security Policy

## Supported Versions

agent-42 is an exploratory, single-author project without formal releases or version tags. Security fixes are applied to the `main` branch only.

| Version | Supported          |
|---------|--------------------|
| `main`  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately. **Do not open a public issue.**

Email the maintainer at **joaohenriquebarbosa21@gmail.com** with:

- A description of the vulnerability and its impact
- Steps to reproduce it
- Any relevant logs, proof-of-concept, or configuration

You can expect an initial acknowledgment within **72 hours**.

## Process

1. **Report received** — we acknowledge your report within 72 hours.
2. **Triage** — we confirm the issue and assess its severity and scope.
3. **Fix** — we develop and test a fix on the `main` branch.
4. **Disclosure** — we coordinate a disclosure timeline with you.
5. **Credit** — with your permission, we credit you in the fix.

## Scope

Reports in the following areas are especially relevant to this project:

- **Injection or unsafe input handling** — in particular the `bash`, `read_file`, and `write_file` tools. Note that only `bash` runs inside the Docker sandbox; `read_file` and `write_file` operate on the **host filesystem**, guarded only by the `_safe_path` prefix check. Path-traversal or sandbox-escape findings against these tools are in scope.
- **Data or credential exposure** — leakage of provider API keys from `.env`, environment variables, logs, or the TUI.
- **Dependency vulnerabilities** — issues in the unpinned third-party packages (`langchain-openai`, `python-dotenv`, `textual`) that materially affect agent-42.

## A note on the threat model

agent-42 runs an LLM that executes arbitrary shell commands and reads and writes files. The `bash` tool is isolated in a container with `network_mode: none`, but the file tools are **not** containerized. Run agent-42 against directories and machines you're comfortable exposing to autonomous file edits, and treat the model's actions as untrusted. This is by design for a coding agent, but it's your responsibility to sandbox the host appropriately for anything sensitive.
