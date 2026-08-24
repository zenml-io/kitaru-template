"""Run the baseline resolver and export real Langfuse traces."""

import argparse
import asyncio
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any

from kitaru.api_models.v1.session_node import NodeType
from kitaru.task.importer import ImportedSession, flatten_nodes
from kitaru_langfuse_importer.importer import parse
from pydantic_ai import Agent

from returns_agent.agent import MODEL, build_agent, build_prompt, get_ticket_input
from returns_agent.fixtures import CASES, TicketInput
from returns_agent.store import MockCommerceStore

REQUEST_OPTIONS = {"timeout_in_seconds": 30, "max_retries": 3}
MODEL_RUN_TIMEOUT_SECONDS = 180
REDACTED_EXPORT_FIELDS = {
    "gen_ai.agent.call.id",
    "gen_ai.conversation.id",
    "gen_ai.response.id",
    "htmlPath",
    "modelId",
    "projectId",
    "public_key",
    "service.instance.id",
    "usagePricingTierId",
    "usagePricingTierName",
}
ACTION_TO_TOOL = {
    "escalate": "escalate_to_human",
    "refund": "issue_refund",
    "replacement": "create_replacement",
}
SENSITIVE_KEY_SUFFIXES = {
    "accesskey",
    "apikey",
    "authorization",
    "credential",
    "password",
    "publickey",
    "secretkey",
    "accesstoken",
    "authtoken",
    "bearertoken",
    "idtoken",
    "refreshtoken",
}
SECRET_PATTERNS = (
    re.compile(r"\b(?:pk|sk)-lf-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def _require_environment() -> None:
    """Raise a focused error when model or tracing credentials are absent."""
    required = (
        "OPENAI_API_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Set {', '.join(missing)} in .env before continuing.")


def _sanitize_export(value: Any) -> Any:
    """Remove credential-shaped telemetry fields from an exported trace."""
    if isinstance(value, dict):
        return {
            key: _sanitize_export(item)
            for key, item in value.items()
            if key not in REDACTED_EXPORT_FIELDS and not _is_sensitive_key(key)
        }
    if isinstance(value, list):
        return [_sanitize_export(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    """Recognize common credential aliases in evolving telemetry metadata."""
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    return any(normalized.endswith(suffix) for suffix in SENSITIVE_KEY_SUFFIXES)


def _validate_disclosure_boundary(value: Any) -> None:
    """Reject secrets and non-fixture email addresses before writing an export."""
    fixture_emails = {ticket.email for ticket in CASES}
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            forbidden = [
                key
                for key in item
                if key in REDACTED_EXPORT_FIELDS or _is_sensitive_key(key)
            ]
            if forbidden:
                raise RuntimeError(
                    f"Generated traces retain forbidden metadata: {forbidden[0]}."
                )
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, str):
            if any(pattern.search(item) for pattern in SECRET_PATTERNS):
                raise RuntimeError("Generated traces retain a credential-shaped value.")
            emails = set(EMAIL_PATTERN.findall(item))
            if not emails <= fixture_emails:
                raise RuntimeError(
                    "Generated traces retain a non-fixture email address."
                )


def _get_trace(client: Any, trace_id: str) -> Any:
    """Wait until one flushed trace has a complete observation graph."""
    deadline = time.monotonic() + 180
    while True:
        try:
            trace = client.api.trace.get(trace_id, request_options=REQUEST_OPTIONS)
            observation_ids = {item.id for item in trace.observations}
            root_count = sum(
                item.parent_observation_id is None for item in trace.observations
            )
            parents_available = all(
                item.parent_observation_id is None
                or item.parent_observation_id in observation_ids
                for item in trace.observations
            )
            observations_complete = all(
                item.name
                and item.output is not None
                and (item.type not in {"GENERATION", "TOOL"} or item.input is not None)
                for item in trace.observations
            )
            if (
                trace.observations
                and root_count == 1
                and parents_available
                and observations_complete
            ):
                return trace
        except Exception:
            if time.monotonic() >= deadline:
                raise
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"Langfuse trace {trace_id} was not queryable after 180 seconds."
            )
        time.sleep(2)


def _get_trace_id(result: Any) -> str:
    """Extract the Langfuse trace ID retained by an instrumented agent run."""
    traceparent = result._traceparent()  # noqa: SLF001
    parts = traceparent.split("-")
    if len(parts) != 4 or len(parts[1]) != 32:
        raise RuntimeError("PydanticAI returned an invalid trace context.")
    return parts[1]


async def _run_ticket(ticket: TicketInput) -> Any:
    """Run one ticket with a bounded provider wait."""
    try:
        async with asyncio.timeout(MODEL_RUN_TIMEOUT_SECONDS):
            return await build_agent(MockCommerceStore(), MODEL).run(
                build_prompt(ticket)
            )
    except TimeoutError as error:
        raise RuntimeError(
            f"Model run for {ticket.ticket_id} timed out after "
            f"{MODEL_RUN_TIMEOUT_SECONDS} seconds."
        ) from error


def _validate_export_documents(documents: list[dict[str, Any]]) -> None:
    """Validate one complete all-cases export before replacing the fixture."""
    expected_inputs = {
        ticket.ticket_id: ticket.model_dump(mode="json") for ticket in CASES
    }
    if len(documents) != len(expected_inputs):
        raise RuntimeError(
            f"Expected exactly {len(expected_inputs)} traces, got {len(documents)}."
        )

    trace_ids = [document.get("id") for document in documents]
    session_ids = [document.get("sessionId") for document in documents]
    if (
        any(not isinstance(value, str) for value in trace_ids + session_ids)
        or len(set(trace_ids)) != len(documents)
        or len(set(session_ids)) != len(documents)
    ):
        raise RuntimeError("Every case must have unique trace and session IDs.")

    observed_inputs: dict[str, Any] = {}
    observed_actions: set[str] = set()
    for document in documents:
        trace_input = document.get("input")
        if not isinstance(trace_input, dict):
            raise RuntimeError("Every trace must retain replayable object inputs.")
        ticket_id = trace_input.get("ticket_id")
        if not isinstance(ticket_id, str) or ticket_id in observed_inputs:
            raise RuntimeError("Every trace must map to one unique fixture ticket.")
        observed_inputs[ticket_id] = trace_input
        if document.get("name") != f"Returns ticket: {ticket_id}":
            raise RuntimeError(f"Trace {ticket_id} has an unexpected name.")
        if document.get("sessionId") != f"returns-{ticket_id}":
            raise RuntimeError(f"Trace {ticket_id} has an unexpected session ID.")

        output = document.get("output")
        if not isinstance(output, dict) or not isinstance(output.get("action"), str):
            raise RuntimeError(f"Trace {ticket_id} has no structured terminal action.")
        observed_actions.add(output["action"])

        observations = document.get("observations")
        if not isinstance(observations, list) or not observations:
            raise RuntimeError(f"Trace {ticket_id} has no observation graph.")
        observation_ids = {
            item.get("id") for item in observations if isinstance(item, dict)
        }
        if len(observation_ids) != len(observations) or None in observation_ids:
            raise RuntimeError(f"Trace {ticket_id} has invalid observation IDs.")
        roots = [
            item
            for item in observations
            if isinstance(item, dict) and item.get("parentObservationId") is None
        ]
        parents_available = all(
            isinstance(item, dict)
            and (
                item.get("parentObservationId") is None
                or item.get("parentObservationId") in observation_ids
            )
            for item in observations
        )
        has_complete_generation = any(
            isinstance(item, dict)
            and item.get("type") == "GENERATION"
            and item.get("name")
            and item.get("input")
            and item.get("output")
            for item in observations
        )
        has_complete_tool = any(
            isinstance(item, dict)
            and item.get("type") == "TOOL"
            and item.get("name")
            and item.get("input") is not None
            and item.get("output") is not None
            for item in observations
        )
        if (
            len(roots) != 1
            or not parents_available
            or not has_complete_generation
            or not has_complete_tool
        ):
            raise RuntimeError(
                f"Trace {ticket_id} has an incomplete observation graph."
            )

    if observed_inputs != expected_inputs:
        raise RuntimeError("Generated trace inputs do not match the fixture matrix.")
    if observed_actions != set(ACTION_TO_TOOL):
        raise RuntimeError(
            "Generated traces must include refund, replacement, and escalation actions."
        )
    _validate_disclosure_boundary(documents)


def _serialize_and_validate_import(documents: list[dict[str, Any]]) -> bytes:
    """Round-trip the export through the installed importer before replacement."""
    content = ("\n".join(json.dumps(trace) for trace in documents) + "\n").encode()
    imported = list(parse(content, {"source_instance": "kitaru-template-generator"}))
    sessions = [item for item in imported if isinstance(item, ImportedSession)]
    if len(imported) != len(documents) or len(sessions) != len(documents):
        raise RuntimeError(
            "The installed importer did not accept every generated trace."
        )

    expected_ids = {ticket.ticket_id for ticket in CASES}
    observed_ids: set[str] = set()
    for session in sessions:
        inputs = session.inputs["turns"][-1]["inputs"]
        ticket = get_ticket_input(inputs)
        if ticket.ticket_id in observed_ids:
            raise RuntimeError("The installed importer produced a duplicate ticket.")
        observed_ids.add(ticket.ticket_id)

        action = session.outputs.get("action")
        if action not in ACTION_TO_TOOL:
            raise RuntimeError(
                f"Imported trace {ticket.ticket_id} has no valid action."
            )
        nodes = flatten_nodes(session.nodes)
        llm_nodes = [node for node in nodes if node.node_type is NodeType.LLM_CALL]
        if not llm_nodes or not any(node.reasoning for node in llm_nodes):
            raise RuntimeError(
                f"Imported trace {ticket.ticket_id} has no model reasoning."
            )
        accepted_actions = [
            node
            for node in nodes
            if node.node_type is NodeType.TOOL_CALL
            and node.tool_name == ACTION_TO_TOOL[action]
            and isinstance(node.outputs, dict)
            and node.outputs.get("accepted") is True
            and node.outputs.get("action") == action
        ]
        if len(accepted_actions) != 1:
            raise RuntimeError(
                f"Imported trace {ticket.ticket_id} does not contain exactly one "
                "accepted terminal action matching its output."
            )
    if observed_ids != expected_ids:
        raise RuntimeError("The installed importer did not preserve every fixture.")
    return content


def _atomic_write(path: Path, content: bytes) -> None:
    """Replace an export only after its complete contents are durable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


async def generate_traces(export_path: Path) -> Path:
    """Run every baseline ticket and write its Langfuse trace as JSONL."""
    _require_environment()
    from langfuse import Langfuse, propagate_attributes

    langfuse = Langfuse()
    Agent.instrument_all()
    trace_data: dict[str, tuple[str, dict[str, Any], dict[str, Any]]] = {}

    for ticket in CASES:
        trace_input = ticket.model_dump(mode="json")
        session_id = f"returns-{ticket.ticket_id}"
        with propagate_attributes(
            session_id=session_id,
            trace_name=f"Returns ticket: {ticket.ticket_id}",
            environment="canonical-example",
            version="baseline-v1",
            tags=["returns-resolution", "kitaru-example"],
            metadata={
                "ticket_id": ticket.ticket_id,
                "agent_release": "baseline-v1",
            },
        ):
            result = await _run_ticket(ticket)
            output = result.output.model_dump(mode="json")
            trace_data[session_id] = (_get_trace_id(result), trace_input, output)
    await asyncio.to_thread(langfuse.flush)
    trace_fetch_limit = asyncio.Semaphore(5)

    async def get_document(session_id: str) -> dict[str, Any]:
        """Fetch and normalize one trace after the shared flush."""
        trace_id, trace_input, output = trace_data[session_id]
        async with trace_fetch_limit:
            trace = await asyncio.to_thread(_get_trace, langfuse, trace_id)
        document = trace.model_dump(mode="json", by_alias=True)
        document["input"] = trace_input
        document["output"] = output
        return _sanitize_export(document)

    traces = await asyncio.gather(
        *(get_document(session_id) for session_id in sorted(trace_data))
    )
    _validate_export_documents(traces)
    content = _serialize_and_validate_import(traces)
    _atomic_write(export_path, content)
    return export_path


def _get_args() -> argparse.Namespace:
    """Parse the trace export destination."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Destination JSONL trace export.")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(generate_traces(_get_args().output))
