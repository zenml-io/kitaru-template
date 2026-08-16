# Repository Guidelines

## Project Structure & Module Organization

`returns_agent/` contains the PydanticAI example: agent construction, typed models,
synthetic fixtures, the in-memory commerce store, and trace generation. Checked-in
Langfuse evidence lives in `traces/langfuse-traces.jsonl`. Tests are under `tests/`;
`test_contract.py` covers agent and trace behavior, `test_repository_contract.py`
protects the public template layout, and `test_e2e.py` exercises the documented
Kitaru workflow. `scripts/run_ci_e2e.py` starts the isolated server used by that
end-to-end test. Keep setup instructions in `README.md` aligned with executable
behavior.

## Build, Test, and Development Commands

- `uv sync --frozen`: install the exact environment from `uv.lock`.
- `uv run ruff format --check .`: verify formatting without changing files.
- `uv run ruff check .`: run import and Python lint checks.
- `uv run python -m pytest -q tests/test_contract.py tests/test_repository_contract.py`:
  run the fast, provider-free CI suite.
- `uv run python scripts/run_ci_e2e.py`: run the full local workflow. This requires
  PostgreSQL on port `5433` and starts its own Kitaru server and worker.

Use `./generate.sh` only when intentionally regenerating traces. It reads `.env`
credentials and replaces the checked-in trace file.

## Coding Style & Naming Conventions

Target Python 3.11 or newer. Ruff enforces an 88-character line length, import
sorting, and the configured `E4`, `E7`, `E9`, `F`, and `I` rules. Use four-space
indentation, type hints for public functions, `snake_case` for functions and
modules, and `PascalCase` for classes. Prefer explicit data flow and small,
deterministic helpers.

## Testing Guidelines

Write pytest tests as `test_<observable_behavior>`. Keep fixtures synthetic and
tests provider-free unless the test is explicitly marked for the isolated E2E
environment. When changing README commands, traces, dependencies, or repository
layout, update the corresponding contract test. Run the fast suite before every
push; run E2E for workflow or integration changes.

## Commit & Pull Request Guidelines

Recent commits use short, imperative subjects such as `Make template independently
runnable`. Keep each commit focused. Pull requests should explain the user-visible
change, list validation performed, and link the relevant issue. Include screenshots
only for visual changes. Never commit `.env`, credentials, private source metadata,
or generated local state from `.kitaru/` or `.zen/`.
