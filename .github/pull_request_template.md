## Description

<!-- What does this PR change, and why? -->

## Related issues

<!-- e.g. Closes #123 -->

## Type of change

- [ ] Bug fix (`fix`)
- [ ] New feature (`feat`)
- [ ] Documentation (`docs`)
- [ ] Refactor (`refactor`)
- [ ] Build / dependencies (`build`)
- [ ] Other:

## How was this tested?

There is no automated test suite, so please describe the manual verification you did:

- [ ] `python app.py` still starts and streams responses
- [ ] `python agent.py` (CLI fallback) still works
- [ ] If the `bash` tool changed: verified it runs in the `agent-42-sandbox` container
- [ ] If `read_file` / `write_file` changed: verified `_safe_path` still blocks paths outside the workspace
- [ ] Other:

## Checklist

- [ ] My commits follow [Conventional Commits](https://www.conventionalcommits.org/)
- [ ] I targeted the `main` branch from a feature branch on my fork
- [ ] I did not add new dependencies without justification
- [ ] I updated the README / docs if behavior or usage changed
- [ ] I read the [Contributing guide](../CONTRIBUTING.md)
