# Contributing to agent-42

Thanks for your interest in improving agent-42. It's a small, exploratory project, so contributions of any size — a typo fix, a clearer docstring, a genuine feature — are all welcome.

Please be respectful in all interactions; this project follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting set up

agent-42 is a flat, script-style Python project. There is no package to install and no build step.

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/agent-42.git
cd agent-42

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install the runtime dependencies
pip install langchain-openai python-dotenv textual

# 4. Bring up the Docker sandbox (needed for the bash tool)
docker compose up -d

# 5. Configure your provider keys
cp .env.example .env
# See the README note: all three provider keys must currently be set,
# even placeholder values, or config.py raises KeyError on import.
```

Run it with `python app.py` (TUI) or `python agent.py` (CLI fallback).

**Requirements:** Python 3.10+ (for `match`/`case` and `X | None` type hints) and Docker.

## Repository layout

All modules live at the repository root — there is no package or subpackage.

| Path                 | What lives here                                                    |
|----------------------|-------------------------------------------------------------------|
| `app.py`             | Textual TUI entrypoint                                             |
| `agent.py`           | `run_turn()` agent loop + CLI `main()`                            |
| `ui.py` / `ui_cli.py`| Textual widgets / plain-terminal UI                               |
| `tools.py`           | The three tool definitions and `execute_tool` dispatch            |
| `context.py`         | Context pruning and compaction                                    |
| `llm.py`             | Provider adapter (`ChatOpenAI` + streaming)                       |
| `config.py`          | Provider configuration from `.env`                                |
| `prompts.py`         | Loads the system and compaction prompts                           |
| `*.txt`, `*.tcss`    | Prompts and Textual CSS                                           |
| `Dockerfile`, `compose.yml` | The sandbox image and container                            |

## Development workflow

1. **Fork** the repository and clone your fork.
2. **Create a branch** off `main` with a descriptive name:
   ```bash
   git checkout -b feat/session-persistence
   ```
3. **Make your change.** Keep the spirit of the project: small, readable, framework-free. Prefer editing existing modules over adding abstractions.
4. **Test it manually.** There is no automated test suite yet, so exercise the change by hand:
   - Run `python app.py` and confirm the TUI still starts and streams.
   - Run `python agent.py` and confirm the CLI fallback still works.
   - If you touched the `bash` tool, verify it runs inside the container (`docker compose ps` should show `agent-42-sandbox`).
   - If you touched `read_file`/`write_file`, confirm `_safe_path` still rejects paths outside the workspace.

   > Adding an actual test suite (`pytest`) is high on the wishlist — a PR that introduces one is very welcome.
5. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/) (see below).
6. **Push** to your fork and **open a pull request** against `main`. Fill in the PR template and describe what you changed and how you verified it.

## Commit message convention

This repository uses **Conventional Commits**. Format:

```
<type>(<optional scope>): <description>
```

Examples from this repo's history: `feat: add auto compact`, `docs: replace ASCII architecture diagram with Mermaid`, `refactor: split agent.py into modules`.

| Type       | When to use it                                                        |
|------------|-----------------------------------------------------------------------|
| `feat`     | A new feature or capability                                           |
| `fix`      | A bug fix                                                             |
| `docs`     | Documentation only (README, comments, this file)                     |
| `refactor` | Code change that neither fixes a bug nor adds a feature              |
| `perf`     | A change that improves performance                                   |
| `style`    | Formatting / whitespace, no behavior change                          |
| `test`     | Adding or adjusting tests                                            |
| `build`    | Build system, dependencies, Dockerfile / compose changes            |
| `ci`       | CI configuration                                                     |
| `chore`    | Maintenance that doesn't fit the above                              |

## Code style

- Target **Python 3.10+**. `match`/`case` and `X | None` unions are already used and encouraged.
- No formatter or linter is configured. Keep to the surrounding style: standard 4-space indentation, clear names, minimal comments. If you'd like to propose adding `ruff`/`black`, open an issue first.
- Don't introduce new dependencies without a reason — part of the point of this project is staying small.

## Reporting bugs and requesting features

Use the issue templates:

- **[Bug report](.github/ISSUE_TEMPLATE/bug_report.yml)** — include reproduction steps, expected vs actual behavior, and your OS.
- **[Feature request](.github/ISSUE_TEMPLATE/feature_request.yml)** — describe the problem before the solution.

For security issues, **do not open a public issue** — see [SECURITY.md](SECURITY.md).

Thanks for contributing.
