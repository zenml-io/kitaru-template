# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A standalone, ready-to-run Kitaru investigation template: a PydanticAI "returns resolver" agent, ten checked-in Langfuse traces (`traces/langfuse-traces.jsonl`), and deterministic tests. All customers, orders, and actions are synthetic; refund/replacement tools only mutate an in-memory store. The teaching walkthrough lives in the Kitaru repo (`docs/book/tutorials/returns-agent`) — this repo deliberately owns only the setup and evidence, not the tutorial content.

## Commands

```bash
uv sync --frozen                      # install the locked environment
uv run ruff format --check .          # formatting check
uv run ruff check .                   # lint (rules: E4, E7, E9, F, I)
uv run python -m pytest -q tests/test_contract.py tests/test_repository_contract.py   # provider-free tests
uv run python -m pytest tests/test_contract.py::test_agent_input_is_replay_safe       # single test
uv run python scripts/run_ci_e2e.py   # full end-to-end (needs PostgreSQL on 127.0.0.1:5433, password "password")
```

`tests/test_e2e.py` is skipped unless `KITARU_CANONICAL_E2E=1`; don't set that yourself — run it through `scripts/run_ci_e2e.py`, which starts an isolated Kitaru server (uvicorn, auth disabled, env stripped of inherited `KITARU_SERVER_*` vars) and sets the gate. Ports are overridable via `KITARU_TEMPLATE_DB_PORT` / `KITARU_TEMPLATE_SERVER_PORT`.

`generate.sh` regenerates the checked-in traces by running the real agent — it needs a `.env` with `OPENAI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY`. Never needed for tests or the import flow.

## The README is executable — treat it as code

`tests/test_e2e.py` extracts the `kitaru` commands from README code blocks via HTML comment markers (`<!-- e2e:register -->`, `<!-- e2e:worker -->`, `<!-- e2e:import -->`, `<!-- e2e:list -->`) and runs them verbatim against a real server. Separately, `tests/test_repository_contract.py` asserts README content: specific strings present/absent, `kitaru worker start` appearing before `kitaru session import`, and fewer than 180 lines total. Any README edit can break CI in non-obvious ways — run both contract test files after touching it.

## Other enforced contracts (tests will fail if violated)

- `pyproject.toml`: `tool.uv.package = false`, `exclude-newer = "3 days"`, and the exact set of `kitaru*` packages exempted in `exclude-newer-package` are all asserted by tests.
- `.github/workflows/ci.yml` must stay secretless and read-only: `permissions: contents: read`, `pull_request` (never `pull_request_target`), no `secrets.` references.
- `.gitignore` must keep `.kitaru/`, `.zen/`, and `evaluator.py` ignored (local investigation state stays out of the public template).
- The checked-in traces must contain no private metadata (`projectId`, `modelId`, `gen_ai.response.id`, etc. — see `REDACTED_EXPORT_FIELDS` in `returns_agent/generate_traces.py`) and no email addresses outside the `@example.test` fixtures. `_sanitize_export` strips these on regeneration; tests re-verify the file.

## Architecture

- `returns_agent/agent.py` — builds the PydanticAI agent. `build_agent(store, model)` registers six tools (`lookup_order`, `get_return_policy`, `check_shipping`, `issue_refund`, `create_replacement`, `escalate_to_human`) as closures over a `MockCommerceStore` instance, with `Resolution` as structured output. `main()` is what a Kitaru worker runs (`python -m returns_agent.agent`): it reads inputs via `kitaru.task.get_task_inputs()`, and `get_ticket_input()` unwraps the `{"turns": [...]}` envelope that imported sessions use, so the same entrypoint works for fresh runs and replays of imported traces.
- `returns_agent/store.py` — deterministic mock commerce backend. Each `MockCommerceStore` deep-copies the fixture orders, so runs are isolated; it enforces refund guards (nonexistent order, double refund, over-refund) and records every action as an `ActionReceipt`.
- `returns_agent/fixtures.py` — `ORDERS`, `POLICIES`, `SHIPMENTS`, and the ten `CASES` ticket inputs. Tickets carry no outcome labels; expected outcomes live only in `tests/canonical_returns_evaluator.py`.
- The e2e test covers the provider-free portion of the documented product loop: register agent → start worker → import traces → evaluate → create an investigation with annotations and verdicts → register a custom evaluator → build cohorts. Experiments are run only after a user or coding agent changes `returns_agent/agent.py` and registers that implementation as a new version.

Dependencies pin Kitaru release-candidate packages (`>=0.22.0rc7,<0.23` etc.); `uv.lock` is committed and CI installs with `--frozen`, so dependency changes require regenerating the lockfile.
