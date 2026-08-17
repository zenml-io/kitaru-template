# Investigate a PydanticAI agent with Kitaru

This repository is a ready-to-run Kitaru investigation template. It contains a PydanticAI returns agent, ten checked-in Langfuse traces with model-generated reasoning summaries, and deterministic tests. All customers, orders, shipments, and actions are synthetic. Refund and replacement tools modify only an in-memory store.

Use this README to prepare the template and import its starting evidence. Continue with the [complete returns-agent tutorial](https://github.com/zenml-io/kitaru/tree/develop/docs/book/tutorials/returns-agent) for the investigation, evaluator, replay, and comparison method.

## Requirements

- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/)
- Docker, only if you use the optional local Kitaru server
- Node.js and `npx`, for installing the optional coding-agent skills

No model-provider or Langfuse credentials are needed for the checked-in import.

## Prepare the template

Clone the repository and install its frozen environment:

```bash
git clone https://github.com/zenml-io/kitaru-template.git
cd kitaru-template
uv sync --frozen
```

Check the currently selected Kitaru server:

```bash
uv run kitaru status
```

If the selected server is healthy, keep using it. It can be local or cloud. If no usable server is selected and you want an isolated local server for the template, start and select one with Docker:

```bash
uv run kitaru login --local
uv run kitaru status
```

Register the included agent from the repository root:

<!-- e2e:register -->

```bash
uv run kitaru agent register \
  returns-resolver \
  --command "python -m returns_agent.agent" \
  --description "Resolve one synthetic returns or delivery request, execute one mock action, and draft the customer reply." \
  --display-version baseline-v1 \
  --working-dir . \
  --timeout-seconds 180 \
  --tool lookup_order \
  --tool get_return_policy \
  --tool check_shipping \
  --tool issue_refund \
  --tool create_replacement \
  --tool escalate_to_human
```

Open a second terminal in this directory and start a worker. No model-provider credentials are needed to import the checked-in traces:

<!-- e2e:worker -->

```bash
uv run kitaru worker start --name kitaru-template-worker
```

Leave the worker running while you import and investigate. Return to the first terminal for the remaining commands.

Import the checked-in Langfuse traces:

<!-- e2e:import -->

```bash
uv run kitaru session import \
  traces/langfuse-traces.jsonl \
  --importer kitaru/langfuse@latest \
  --agent returns-resolver@1 \
  --tag returns-baseline \
  --params '{"source_instance":"kitaru-template"}' \
  --media-type application/x-ndjson \
  --wait
```

Confirm that all ten sessions are available:

<!-- e2e:list -->

```bash
uv run kitaru session list \
  --tag returns-baseline \
  --origin imported \
  --size 20
```

## Continue with a coding agent

Install the Kitaru skills:

```bash
npx skills add zenml-io/kitaru-skills
```

Then give your coding agent this prompt:

```text
Use the kitaru-guided-tour skill to investigate the included PydanticAI
returns agent. The registered agent is returns-resolver and its imported
sessions have the returns-baseline tag. Use the checked-in Langfuse evidence,
show me the recorded behavior before asking for a judgment, and explain what
each step does and why it matters. When the investigation identifies a fix,
change returns_agent/agent.py, register that command as a new agent version,
and run the experiment against the changed version.
```

The skill stores investigation state in Kitaru and can resume from existing agents, import jobs, tags, and sessions. The [complete tutorial](https://github.com/zenml-io/kitaru/tree/develop/docs/book/tutorials/returns-agent) explains the five-step method and the commands behind it.

Experiment candidates come from changes to `returns_agent/agent.py`. Register
that implementation as a new agent version so each experiment measures the
code under investigation.

## Validate the repository

Run the provider-free checks:

```bash
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run python -m pytest -q tests/test_contract.py tests/test_repository_contract.py
```

The end-to-end CI runner additionally needs an isolated PostgreSQL server on port `5433`:

```bash
uv run python scripts/run_ci_e2e.py
```

The runner starts and stops its own Kitaru server. The end-to-end test starts and stops its worker and prints the captured logs when either process fails.

When you finish investigating, press `Ctrl-C` in the worker terminal. If you selected the temporary local server for this template, disconnect from it with `uv run kitaru logout`.
