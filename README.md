# Investigate a PydanticAI agent with Kitaru

This repository is a ready-to-run Kitaru investigation template. It contains a PydanticAI returns agent, 30 checked-in Langfuse traces with model-generated reasoning summaries, and deterministic tests. All customers, orders, shipments, and actions are synthetic. Refund and replacement tools modify only an in-memory store.

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

The expanded tour runs against a Kitaru Cloud server. If its URL is not already selected, set it explicitly:

```bash
export KITARU_API_URL="https://your-kitaru-server.example"
```

Use an inherited `KITARU_API_KEY` when one is already configured. Otherwise authenticate interactively with `uv run kitaru login "$KITARU_API_URL"`. The tour checks connectivity without printing credentials and does not switch to a local server.

If the selected server is healthy, keep using it. The template itself supports local or cloud servers; the expanded tour continues only with the cloud target above. Check whether this template is already set up there:

```bash
uv run kitaru agent get returns-resolver
uv run kitaru session list \
  --agent returns-resolver \
  --tag returns-baseline \
  --origin imported \
  --size 30
```

If the agent and all 30 imported sessions already exist, skip to [Continue with a coding agent](#continue-with-a-coding-agent). The expanded tour will inspect and resume that state before it creates anything. If neither exists, continue with the registration below. If only part of the setup exists, or `returns-resolver` belongs to another project, select a different server so the fixed template names do not collide.

If no usable server is selected and you want an isolated local server for the template, start and select one with Docker:

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

Open a second terminal in this directory and start a worker. A new terminal does not inherit exports from the first one, so repeat the `KITARU_API_URL` export there and make the same `KITARU_API_KEY` available when you selected Cloud through environment variables. Run `uv run kitaru status` in the second terminal and confirm that it reports the same Cloud URL before starting the worker. No model-provider credentials are needed to import the checked-in traces:

<!-- e2e:worker -->

```bash
uv run kitaru worker start --name kitaru-template-worker --concurrency 10 \
  --blob-cache-root .kitaru/cache/blobs \
  --payload-cache-root .kitaru/cache/payloads
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

Confirm that all 30 sessions are available:

<!-- e2e:list -->

```bash
uv run kitaru session list \
  --tag returns-baseline \
  --origin imported \
  --size 30
```

## Continue with a coding agent

For a compact visual introduction to the synthetic returns agent and the category policy it should apply, open [returns-agent-guide.html](returns-agent-guide.html) in a browser before starting the tour.

Install `kitaru-workshop-tour` from the compatible companion `kitaru-skills` feature checkout. Replace the example absolute path with that checkout's path:

```bash
npx skills add /absolute/path/to/kitaru-skills \
  --skill kitaru-workshop-tour \
  --copy \
  --yes
```

Then give your coding agent this prompt:

```text
Use the kitaru-workshop-tour skill with the registered returns-resolver agent
and the sessions tagged returns-baseline. Survey all 30 sessions, show me the
evidence-selected shortlist, and ask me for the required human judgments.
Once we confirm a behavior to improve, help me turn it into one evaluator and
test one small change. Show me the full run plan and ask before changing code
or starting paid model work.
```

The skill stores investigation state in Kitaru and can resume from existing agents, import jobs, tags, and sessions. The [complete tutorial](https://github.com/zenml-io/kitaru/tree/develop/docs/book/tutorials/returns-agent) explains the five-step method and the commands behind it.

### Already familiar with Kitaru?

If you have read the [Kitaru quickstart](https://docs.zenml.io/kitaru/getting-started/quickstart) and understand how Kitaru moves from recorded evidence to an evaluator and replay, you can use the less scripted investigation skill instead:

```text
Use kitaru-investigation with the registered returns-resolver agent and the
sessions tagged returns-baseline. Start from the recorded evidence and help
me decide what is worth investigating. Once I accept a finding, help me turn
it into an evaluator and test one bounded change. Ask before creating
resources, changing code, or starting paid replay.
```

If the investigation points to agent behavior, change `returns_agent/agent.py` and register the new implementation as another agent version before running the experiment.

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

When you are ready to investigate your own agent, open its project and start with `kitaru-investigation`.
