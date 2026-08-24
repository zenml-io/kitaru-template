"""Contract tests for the canonical returns-resolution example."""

import asyncio
import copy
import json
import re
import tomllib
from collections import Counter
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from kitaru.api_models.v1.session_node import NodeType
from kitaru.task.importer import ImportedSession, flatten_nodes
from kitaru_langfuse_importer.importer import parse

from returns_agent.agent import (
    build_agent,
    build_prompt,
    get_ticket_input,
)
from returns_agent.fixtures import CASES, ORDERS
from returns_agent.generate_traces import (
    REDACTED_EXPORT_FIELDS,
    _atomic_write,
    _get_trace,
    _get_trace_id,
    _run_ticket,
    _sanitize_export,
    _serialize_and_validate_import,
    _validate_disclosure_boundary,
    _validate_export_documents,
)
from returns_agent.store import MockCommerceStore
from scripts.run_ci_e2e import _get_server_environment
from tests.canonical_returns_evaluator import (
    CASE_FAMILIES,
    INTENDED_CONTROL_TICKETS,
    REVIEWED_OUTCOMES,
)
from tests.canonical_returns_evaluator import evaluate as evaluate_canonical_outcome

EXAMPLE_DIR = Path(__file__).parents[1]
TRACE_PATH = EXAMPLE_DIR / "traces" / "langfuse-traces.jsonl"


def test_fixture_corpus_contains_thirty_distinct_synthetic_inputs() -> None:
    """Keep the population complete, synthetic, and free of oracle labels."""
    assert len(CASES) == 30
    assert len({ticket.ticket_id for ticket in CASES}) == 30
    assert all(ticket.email.endswith("@example.test") for ticket in CASES)
    public_fixture_data = [ticket.model_dump(mode="json") for ticket in CASES]
    public_fixture_text = json.dumps(public_fixture_data)
    assert "expected_action" not in public_fixture_text
    assert "behavior_family" not in public_fixture_text
    assert "ordinary_control" not in public_fixture_text


def test_test_oracle_covers_four_repeated_families_with_a_control_majority() -> None:
    """Keep hidden fixture intent exhaustive without exposing it to the agent."""
    ticket_ids = {ticket.ticket_id for ticket in CASES}
    assert set(REVIEWED_OUTCOMES) == ticket_ids
    assert set(CASE_FAMILIES) == ticket_ids
    assert INTENDED_CONTROL_TICKETS < ticket_ids
    assert len(INTENDED_CONTROL_TICKETS) > len(CASES) / 2

    family_counts = Counter(CASE_FAMILIES.values())
    assert set(family_counts) == {
        "escalation_judgment",
        "policy_action_alignment",
        "resolution_path",
        "tool_efficiency",
    }
    assert all(count >= 4 for count in family_counts.values())
    assert {outcome[0] for outcome in REVIEWED_OUTCOMES.values()} == {
        "escalate",
        "refund",
        "replacement",
    }


def test_fixture_matrix_includes_nearby_policy_and_escalation_boundaries() -> None:
    """Keep neighboring cases around the policy limits used in the expanded tour."""
    assert ORDERS["48301"].days_since_delivery == 29
    assert ORDERS["48302"].days_since_delivery == 31
    assert ORDERS["48303"].days_since_delivery == 13
    assert ORDERS["48304"].days_since_delivery == 15
    assert ORDERS["48307"].amount_paid == Decimal("150.00")
    assert ORDERS["48308"].amount_paid == Decimal("151.00")


def test_mock_store_records_only_local_refund_side_effects() -> None:
    """Record a valid refund in an isolated store and reject an over-refund."""
    store = MockCommerceStore()

    accepted = store.issue_refund("48213", Decimal("98.00"))
    rejected = MockCommerceStore().issue_refund("48213", Decimal("120.00"))

    assert accepted.accepted is True
    assert accepted.receipt_id == "mock-refund-48213"
    assert store.orders["48213"].already_refunded is True
    assert rejected.accepted is False
    assert rejected.receipt_id is None


def test_order_lookup_can_retry_by_email_after_a_wrong_number() -> None:
    """Provide one natural repeated-tool path for the starting-point evaluator."""
    store = MockCommerceStore()

    missing = store.lookup_order(order_id="48228")
    recovered = store.lookup_order(email="riley@example.test")

    assert missing.found is False
    assert recovered.found is True
    assert [order.order_id for order in recovered.orders] == ["48222"]


def test_policy_lookup_normalizes_product_aliases_without_crashing() -> None:
    """Keep model-generated category variants recoverable inside the trace."""
    result = MockCommerceStore().get_return_policy("tote")

    assert result.found is True
    assert result.policy is not None
    assert result.policy.category == "accessories"


def test_agent_input_is_replay_safe() -> None:
    """Unwrap imported inputs and build the agent prompt."""
    ticket = CASES[0]
    imported = {
        "schema_version": 1,
        "turns": [{"source_trace_id": "trace-1", "inputs": ticket.model_dump()}],
    }

    assert get_ticket_input(imported) == ticket
    prompt = build_prompt(ticket)
    assert ticket.body in prompt


def test_baseline_agent_exposes_the_mock_commerce_tools() -> None:
    """Keep the example trace graph focused on investigation and terminal actions."""
    agent = build_agent(MockCommerceStore(), "test")

    assert agent.model_settings == {"openai_reasoning_summary": "auto"}
    assert set(agent._function_toolset.tools) == {
        "lookup_order",
        "get_return_policy",
        "check_shipping",
        "issue_refund",
        "create_replacement",
        "escalate_to_human",
    }


def test_checked_in_langfuse_export_contains_replayable_tool_traces() -> None:
    """Keep one imported baseline session per ticket with LLM and tool nodes."""
    sessions = [
        item
        for item in parse(
            TRACE_PATH.read_bytes(),
            {"source_instance": "canonical-returns-example"},
        )
        if isinstance(item, ImportedSession)
    ]

    assert len(sessions) == len(CASES)
    assert {session.name for session in sessions} == {
        f"Returns ticket: {ticket.ticket_id}" for ticket in CASES
    }
    imported_inputs = {
        session.inputs["turns"][-1]["inputs"]["ticket_id"]: session.inputs["turns"][-1][
            "inputs"
        ]
        for session in sessions
    }
    fixture_inputs = {
        ticket.ticket_id: ticket.model_dump(mode="json") for ticket in CASES
    }
    assert imported_inputs == fixture_inputs
    assert {session.outputs["action"] for session in sessions} == {
        "refund",
        "replacement",
        "escalate",
    }
    for session in sessions:
        nodes = flatten_nodes(session.nodes)
        assert [node.name for node in session.nodes] == ["agent run"]
        assert all(node.name != "resolve-ticket" for node in nodes)
        llm_nodes = [node for node in nodes if node.node_type is NodeType.LLM_CALL]
        assert llm_nodes
        assert any(node.reasoning for node in llm_nodes)
        assert any(node.node_type is NodeType.TOOL_CALL for node in nodes)

    evaluations_by_ticket = {
        session.inputs["turns"][-1]["inputs"]["ticket_id"]: evaluate_canonical_outcome(
            SimpleNamespace(
                session=SimpleNamespace(
                    inputs=session.inputs,
                    outputs=session.outputs,
                ),
                nodes=flatten_nodes(session.nodes),
            )
        )
        for session in sessions
    }
    passing_tickets = {
        ticket_id
        for ticket_id, result in evaluations_by_ticket.items()
        if result.passed is True
    }
    failing_tickets = set(evaluations_by_ticket) - passing_tickets
    assert len(passing_tickets) > len(CASES) / 2
    assert len(failing_tickets) >= 4
    assert {CASE_FAMILIES[ticket_id] for ticket_id in passing_tickets} == set(
        CASE_FAMILIES.values()
    )
    assert len({CASE_FAMILIES[ticket_id] for ticket_id in failing_tickets}) >= 2


def test_trace_generator_extracts_the_instrumented_run_trace_id() -> None:
    """Fetch the trace emitted by PydanticAI without adding a wrapper span."""

    class Result:
        def _traceparent(self) -> str:
            return "00-0123456789abcdef0123456789abcdef-fedcba9876543210-01"

    assert _get_trace_id(Result()) == "0123456789abcdef0123456789abcdef"


def test_trace_generator_rejects_partial_and_duplicate_populations() -> None:
    """Fail the all-cases generation before replacing the checked-in corpus."""
    with pytest.raises(RuntimeError, match="exactly 30 traces"):
        _validate_export_documents([])

    duplicate = {
        "id": "trace-1",
        "name": "Returns ticket: ticket-001",
        "sessionId": "returns-ticket-001",
        "input": CASES[0].model_dump(mode="json"),
        "output": {"action": "refund"},
        "observations": [{"id": "root-1", "parentObservationId": None}],
    }
    with pytest.raises(RuntimeError, match="unique trace and session IDs"):
        _validate_export_documents([duplicate] * len(CASES))


def test_trace_generator_rejects_empty_observation_shells() -> None:
    """Wait for evidence payloads instead of accepting an eventual-consistency shell."""
    documents = [
        {
            "id": f"trace-{ticket.ticket_id}",
            "name": f"Returns ticket: {ticket.ticket_id}",
            "sessionId": f"returns-{ticket.ticket_id}",
            "input": ticket.model_dump(mode="json"),
            "output": {"action": REVIEWED_OUTCOMES[ticket.ticket_id][0]},
            "observations": [
                {
                    "id": f"root-{ticket.ticket_id}",
                    "parentObservationId": None,
                    "type": "AGENT",
                },
                {
                    "id": f"generation-{ticket.ticket_id}",
                    "parentObservationId": f"root-{ticket.ticket_id}",
                    "type": "GENERATION",
                },
                {
                    "id": f"tool-{ticket.ticket_id}",
                    "parentObservationId": f"root-{ticket.ticket_id}",
                    "type": "TOOL",
                },
            ],
        }
        for ticket in CASES
    ]

    with pytest.raises(RuntimeError, match="incomplete observation graph"):
        _validate_export_documents(documents)


def test_trace_polling_waits_for_populated_observations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not accept an eventually consistent trace before payloads arrive."""
    incomplete = SimpleNamespace(
        observations=[
            SimpleNamespace(
                id="root",
                parent_observation_id=None,
                name="agent run",
                type="AGENT",
                input={},
                output={},
            ),
            SimpleNamespace(
                id="generation",
                parent_observation_id="root",
                name="chat",
                type="GENERATION",
                input={},
                output=None,
            ),
        ]
    )
    complete = copy.deepcopy(incomplete)
    complete.observations[-1].output = {"message": "complete"}
    responses = iter([incomplete, complete])
    get = SimpleNamespace(calls=0)

    def get_trace(*args: object, **kwargs: object) -> SimpleNamespace:
        get.calls += 1
        return next(responses)

    get.__call__ = get_trace
    client = SimpleNamespace(api=SimpleNamespace(trace=SimpleNamespace(get=get_trace)))
    monkeypatch.setattr("returns_agent.generate_traces.time.sleep", lambda _: None)

    assert _get_trace(client, "trace-id") is complete
    assert get.calls == 2


def test_trace_generator_bounds_each_model_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail one stuck provider call without reaching corpus replacement."""

    class StuckAgent:
        async def run(self, prompt: str) -> None:
            await asyncio.Event().wait()

    monkeypatch.setattr(
        "returns_agent.generate_traces.build_agent", lambda *args: StuckAgent()
    )
    monkeypatch.setattr(
        "returns_agent.generate_traces.MODEL_RUN_TIMEOUT_SECONDS", 0.001
    )

    with pytest.raises(RuntimeError, match=r"ticket-001 timed out after 0\.001"):
        asyncio.run(_run_ticket(CASES[0]))


def test_import_round_trip_rejects_missing_reasoning() -> None:
    """Reject an otherwise importable corpus whose model evidence is empty."""
    documents = [json.loads(line) for line in TRACE_PATH.read_text().splitlines()]
    for observation in documents[0]["observations"]:
        if observation.get("type") == "GENERATION":
            observation["input"] = {"messages": []}
            observation["output"] = [
                {
                    "role": "assistant",
                    "parts": [{"type": "text", "content": "No reasoning."}],
                }
            ]

    with pytest.raises(RuntimeError, match="has no model reasoning"):
        _serialize_and_validate_import(documents)


def test_import_round_trip_rejects_mismatched_terminal_action() -> None:
    """Reject a reported resolution without one matching accepted tool action."""
    documents = [json.loads(line) for line in TRACE_PATH.read_text().splitlines()]
    action = documents[0]["output"]["action"]
    terminal_tool = {
        "escalate": "escalate_to_human",
        "refund": "issue_refund",
        "replacement": "create_replacement",
    }[action]
    terminal = next(
        observation
        for observation in documents[0]["observations"]
        if observation.get("name") == terminal_tool
    )
    terminal["output"]["accepted"] = False

    with pytest.raises(RuntimeError, match="exactly one accepted terminal action"):
        _serialize_and_validate_import(documents)


def test_atomic_export_write_preserves_previous_corpus_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Leave the previous checked-in corpus intact when replacement fails."""
    export_path = tmp_path / "traces.jsonl"
    export_path.write_bytes(b"previous\n")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError(f"cannot replace {source} with {destination}")

    monkeypatch.setattr("returns_agent.generate_traces.os.replace", fail_replace)

    with pytest.raises(OSError, match="cannot replace"):
        _atomic_write(export_path, b"replacement\n")

    assert export_path.read_bytes() == b"previous\n"
    assert list(tmp_path.iterdir()) == [export_path]


def test_checked_in_export_omits_source_instance_identifiers() -> None:
    """Keep the public trace graph while removing private source metadata."""
    documents = [json.loads(line) for line in TRACE_PATH.read_text().splitlines()]
    forbidden = REDACTED_EXPORT_FIELDS
    present: set[str] = set()
    pending: list[object] = [documents]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            present.update(value.keys() & forbidden)
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    assert not present, present

    strings: set[str] = set()
    pending = [documents]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, str):
            strings.add(value)
    fixture_emails = {ticket.email for ticket in CASES}
    trace_emails = {
        email
        for value in strings
        for email in re.findall(r"[\w.+-]+@[\w.-]+\.\w+", value)
    }
    assert trace_emails <= fixture_emails
    trace_text = "\n".join(strings)
    assert not re.search(r"\b(?:pk|sk)-lf-[A-Za-z0-9_-]{8,}", trace_text)
    assert not re.search(r"\bsk-[A-Za-z0-9_-]{20,}", trace_text)


def test_trace_generator_removes_publicly_forbidden_metadata() -> None:
    """Keep regenerated exports inside the checked-in disclosure boundary."""
    forbidden = {
        "gen_ai.agent.call.id",
        "gen_ai.conversation.id",
        "gen_ai.response.id",
        "htmlPath",
        "modelId",
        "projectId",
        "service.instance.id",
        "usagePricingTierId",
        "usagePricingTierName",
    }
    assert forbidden <= REDACTED_EXPORT_FIELDS
    document = {name: "private" for name in forbidden}
    document["nested"] = [{"public_key": "credential", "safe": "value"}]

    assert _sanitize_export(document) == {"nested": [{"safe": "value"}]}


def test_trace_generator_rejects_unknown_credential_aliases() -> None:
    """Reject evolving metadata aliases before they reach the public corpus."""
    document = {
        "metadata": {"apiKey": "sk-aaaaaaaaaaaaaaaaaaaaaaaa"},
        "input": {"email": "private@example.com"},
    }

    assert _sanitize_export(document) == {
        "metadata": {},
        "input": {"email": "private@example.com"},
    }
    with pytest.raises(RuntimeError, match="non-fixture email"):
        _validate_disclosure_boundary(_sanitize_export(document))


def test_trace_generator_preserves_token_usage_telemetry() -> None:
    """Keep resource-evaluator inputs while removing credential-bearing tokens."""
    document = {
        "promptTokens": 100,
        "completionTokens": 20,
        "totalTokens": 120,
        "timeToFirstToken": 0.5,
        "auth_token": "private",
    }

    assert _sanitize_export(document) == {
        "promptTokens": 100,
        "completionTokens": 20,
        "totalTokens": 120,
        "timeToFirstToken": 0.5,
    }


def test_e2e_server_environment_ignores_inherited_kitaru_server(monkeypatch) -> None:
    """Never redirect the isolated E2E workflow to a caller's Kitaru server."""
    monkeypatch.setenv("KITARU_SERVER_DATABASE_URL", "postgresql://production")
    monkeypatch.setenv("KITARU_SERVER_DB_HOST", "production.example.test")
    monkeypatch.setenv("KITARU_TEMPLATE_DB_PORT", "55433")

    environment = _get_server_environment()

    assert "KITARU_SERVER_DATABASE_URL" not in environment
    assert environment["KITARU_SERVER_DB_HOST"] == "127.0.0.1"
    assert environment["KITARU_SERVER_DB_PORT"] == "55433"
    assert environment["KITARU_SERVER_DB_NAME"].startswith("kitaru_template_e2e_")


def test_example_declares_its_pypi_dependencies() -> None:
    """Keep the example isolated from the repository development environment."""
    project = tomllib.loads((EXAMPLE_DIR / "pyproject.toml").read_text())
    dependencies = project["project"]["dependencies"]
    uv_config = project["tool"]["uv"]

    assert uv_config["package"] is False
    assert uv_config["exclude-newer"] == "3 days"
    assert {
        name
        for name, cutoff in uv_config["exclude-newer-package"].items()
        if cutoff is False
    } == {
        "kitaru",
        "kitaru-braintrust-importer",
        "kitaru-evaluator",
        "kitaru-jsonl-importer",
        "kitaru-langfuse-importer",
        "kitaru-langgraph",
        "kitaru-langsmith-importer",
        "kitaru-openai-agents",
        "kitaru-pydantic-ai",
    }
    assert any(
        requirement.startswith("kitaru[cli,mcp,server,worker]")
        for requirement in dependencies
    )
    assert any(
        requirement.startswith("kitaru-pydantic-ai[openai]")
        for requirement in dependencies
    )
    assert any(
        requirement.startswith("kitaru-langfuse-importer")
        for requirement in dependencies
    )
    assert (EXAMPLE_DIR / "uv.lock").is_file()
