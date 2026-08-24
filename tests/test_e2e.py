"""Run the canonical CLI walkthrough against a real local Kitaru server."""

import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from kitaru.task.importer import ImportedSession, flatten_nodes
from kitaru_langfuse_importer.importer import parse

from returns_agent.fixtures import CASES
from tests.canonical_returns_evaluator import evaluate as evaluate_canonical_outcome

EXAMPLE_DIR = Path(__file__).parents[1]
README_PATH = EXAMPLE_DIR / "README.md"
TEST_ASSETS_DIR = EXAMPLE_DIR / "tests"
EVALUATOR_FIXTURE_PATH = TEST_ASSETS_DIR / "canonical_returns_evaluator.py"
TRACE_PATH = EXAMPLE_DIR / "traces" / "langfuse-traces.jsonl"
CLI = Path(sys.executable).with_name("kitaru")

pytestmark = pytest.mark.skipif(
    os.environ.get("KITARU_CANONICAL_E2E") != "1",
    reason="Set KITARU_CANONICAL_E2E=1 against an isolated local server.",
)


def _subprocess_environment() -> dict[str, str]:
    """Build the environment used by the CLI and worker."""
    environment = os.environ.copy()
    environment["KITARU_API_URL"] = os.environ["KITARU_CANONICAL_SERVER_URL"]
    environment["KITARU_API_KEY"] = os.environ["KITARU_CANONICAL_API_KEY"]
    return environment


def _get_readme_command(name: str) -> list[str]:
    """Return one marked Kitaru command from the public setup contract."""
    readme = README_PATH.read_text()
    marker = f"<!-- e2e:{name} -->"
    marker_start = readme.index(marker)
    block_start = readme.index("```bash\n", marker_start) + len("```bash\n")
    block_end = readme.index("\n```", block_start)
    command = readme[block_start:block_end].replace("\\\n", " ")
    arguments = shlex.split(command)
    assert arguments[:3] == ["uv", "run", "kitaru"]
    return arguments[3:]


def _run(
    command: list[str],
    *,
    cwd: Path = EXAMPLE_DIR,
    timeout: float = 300,
) -> subprocess.CompletedProcess[str]:
    """Run one walkthrough command with actionable failure output."""
    result = subprocess.run(
        command,
        cwd=cwd,
        env=_subprocess_environment(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _cli(*arguments: str, timeout: float = 300) -> dict[str, Any]:
    """Run one CLI command and return its JSON document."""
    result = _run([str(CLI), "--output", "json", *arguments], timeout=timeout)
    return json.loads(result.stdout)


def _items(*arguments: str) -> list[dict[str, Any]]:
    """Return typed-looking item dictionaries from one list command."""
    document = _cli(*arguments)
    items = document.get("items")
    assert isinstance(items, list), document
    return items


def _ticket_id(session: dict[str, Any]) -> str:
    """Read the latest imported ticket id from a session document."""
    inputs = session["inputs"]
    if isinstance(inputs, dict) and isinstance(inputs.get("turns"), list):
        inputs = inputs["turns"][-1]["inputs"]
    assert isinstance(inputs, dict)
    ticket_id = inputs.get("ticket_id")
    assert isinstance(ticket_id, str)
    return ticket_id


def _action(session: dict[str, Any]) -> str:
    """Read the imported session's reported terminal action."""
    outputs = session["outputs"]
    assert isinstance(outputs, dict)
    action = outputs.get("action")
    assert isinstance(action, str)
    return action


def _write_test_evaluator(path: Path) -> None:
    """Copy the test-only evaluator used by the deterministic smoke path."""
    shutil.copyfile(EVALUATOR_FIXTURE_PATH, path)


def _wait_for_worker(name: str, process: subprocess.Popen[str]) -> None:
    """Wait until the foreground worker has registered with the server."""
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Worker exited before registration with {process.returncode}."
            )
        workers = _items("worker", "list")
        if any(
            item.get("name") == name and item.get("status") == "live"
            for item in workers
        ):
            return
        time.sleep(0.25)
    raise RuntimeError("Worker did not become live within 30 seconds.")


def test_canonical_example_completes_import_to_cohorts(tmp_path: Path) -> None:
    """Exercise the provider-free import, evaluation, and cohort workflow."""
    assert CLI.exists()
    _cli("status")
    _cli(*_get_readme_command("register"))

    worker_arguments = _get_readme_command("worker")
    worker_name = worker_arguments[worker_arguments.index("--name") + 1]
    worker_log_path = Path(
        os.environ.get("KITARU_CANONICAL_WORKER_LOG", tmp_path / "worker.log")
    )
    with worker_log_path.open("w+", encoding="utf-8") as worker_log:
        worker = subprocess.Popen(
            [
                str(CLI),
                "--output",
                "jsonl",
                *worker_arguments,
                "--poll-interval",
                "0.1",
                "--blob-cache-root",
                str(tmp_path / "blobs"),
                "--payload-cache-root",
                str(tmp_path / "payloads"),
                "--timeout",
                "300",
            ],
            cwd=EXAMPLE_DIR,
            env=_subprocess_environment(),
            text=True,
            stdout=worker_log,
            stderr=subprocess.STDOUT,
        )
        try:
            _wait_for_worker(worker_name, worker)
            _cli(*_get_readme_command("import"), "--timeout", "180")

            baseline = _items(*_get_readme_command("list"))
            assert len(baseline) == 30
            sessions_by_ticket = {_ticket_id(item): item["id"] for item in baseline}
            assert set(sessions_by_ticket) == {ticket.ticket_id for ticket in CASES}

            _cli(
                "session",
                "evaluate",
                "--tag",
                "returns-baseline",
                "--evaluator",
                "kitaru/cost@latest",
                "--evaluator",
                "kitaru/latency@latest",
                "--evaluator",
                "kitaru/tool-call-patterns@latest",
                "--wait",
                "--timeout",
                "180",
            )

            reviewed_tickets = {
                "ticket-012": ("problematic", "escalate"),
                "ticket-017": ("acceptable", "refund"),
                "ticket-001": ("acceptable", "refund"),
            }
            action_to_tool = {
                "refund": "issue_refund",
                "replacement": "create_replacement",
                "escalate": "escalate_to_human",
            }
            evidence_nodes: dict[str, str] = {}
            investigation_arguments = [
                "investigation",
                "create",
                "refund-policy-review",
                "--agent",
                "returns-resolver",
                "--description",
                "Review risky refunds and nearby valid refund behavior.",
            ]
            for ticket_id in reviewed_tickets:
                session_id = sessions_by_ticket[ticket_id]
                session = next(item for item in baseline if item["id"] == session_id)
                terminal_tool = action_to_tool[_action(session)]
                nodes = _items(
                    "session",
                    "nodes",
                    session_id,
                    "--include-payloads",
                    "--size",
                    "100",
                )
                evidence = next(
                    node
                    for node in reversed(nodes)
                    if node.get("tool_name") == terminal_tool
                )
                evidence_nodes[ticket_id] = evidence["id"]
                question = (
                    "Is this outcome acceptable, problematic, or uncertain, and "
                    "what should the agent have done in this case?"
                )
                investigation_arguments.extend(
                    [
                        "--session",
                        session_id,
                        "--session-question",
                        f"{session_id}:outcome={question}",
                    ]
                )

            investigation = _cli(*investigation_arguments)["item"]
            investigation_id = investigation["id"]
            linked_sessions = _items(
                "investigation",
                "session",
                "list",
                investigation_id,
                "--size",
                "20",
            )
            assert len(linked_sessions) == 3
            links_by_session = {
                item["session_id"]: item["id"] for item in linked_sessions
            }
            for ticket_id, (verdict, expected_action) in reviewed_tickets.items():
                session_id = sessions_by_ticket[ticket_id]
                investigation_session_id = links_by_session[session_id]
                selector = json.dumps(
                    {"node_id": evidence_nodes[ticket_id]}, separators=(",", ":")
                )
                _cli(
                    "annotation",
                    "create",
                    "--session",
                    session_id,
                    "--selector",
                    selector,
                    "--value",
                    json.dumps(
                        "Agent observation: Inspect the reported action beside "
                        "the highlighted terminal tool evidence."
                    ),
                )
                if ticket_id == "ticket-012":
                    _cli(
                        "annotation",
                        "create",
                        "--investigation-session",
                        investigation_session_id,
                        "--question-key",
                        "outcome",
                        "--selector",
                        selector,
                        "--value",
                        json.dumps(
                            f"The agent should have {expected_action}d because "
                            "the accepted refund bypassed the required approval path."
                        ),
                    )
                _cli(
                    "investigation",
                    "session",
                    "verdict",
                    investigation_id,
                    session_id,
                    verdict,
                )

            _cli("investigation", "update", investigation_id, "--status", "completed")
            completed_investigation = _cli("investigation", "get", investigation_id)[
                "item"
            ]
            assert completed_investigation["status"] == "completed"
            assert completed_investigation["completed_sessions"] == 3
            annotation_filter = json.dumps(
                {
                    "field": "investigation_id",
                    "op": "eq",
                    "value": investigation_id,
                },
                separators=(",", ":"),
            )
            annotations = _items(
                "annotation",
                "list",
                "--filter",
                annotation_filter,
                "--size",
                "100",
            )
            assert len(annotations) == 1
            assert annotations[0]["selector"] is not None
            assert isinstance(annotations[0]["value"], str)
            assert all(
                not (isinstance(item["value"], dict) and "judgment" in item["value"])
                for item in annotations
            )

            evaluator_path = tmp_path / "returns_policy.py"
            _write_test_evaluator(evaluator_path)
            _cli(
                "evaluator",
                "test",
                str(evaluator_path),
                "--entrypoint",
                "evaluate",
            )
            _cli(
                "evaluator",
                "register",
                "returns-policy",
                "--script",
                str(evaluator_path),
                "--entrypoint",
                "evaluate",
                "--description",
                "Check reviewed returns outcomes.",
                "--display-version",
                "1.0",
            )
            _cli(
                "session",
                "evaluate",
                "--tag",
                "returns-baseline",
                "--evaluator",
                "returns-policy@1",
                "--wait",
                "--timeout",
                "180",
            )
            policy_filter = '{"field":"name","op":"eq","value":"policy_correct"}'
            baseline_policy = _items(
                "evaluation", "list", "--filter", policy_filter, "--size", "100"
            )
            assert len(baseline_policy) == 30
            imported_sessions = [
                item
                for item in parse(
                    TRACE_PATH.read_bytes(),
                    {"source_instance": "kitaru-template-e2e"},
                )
                if isinstance(item, ImportedSession)
            ]
            expected_policy = {
                sessions_by_ticket[
                    session.inputs["turns"][-1]["inputs"]["ticket_id"]
                ]: evaluate_canonical_outcome(
                    SimpleNamespace(
                        session=SimpleNamespace(
                            inputs=session.inputs,
                            outputs=session.outputs,
                        ),
                        nodes=flatten_nodes(session.nodes),
                    )
                ).passed
                for session in imported_sessions
            }
            assert {
                item["session_id"]: item["passed"] for item in baseline_policy
            } == expected_policy

            _cli(
                "cohort",
                "create",
                "reviewed-returns-baseline",
                "--agent",
                "returns-resolver",
                "--session",
                sessions_by_ticket["ticket-012"],
                "--session",
                sessions_by_ticket["ticket-017"],
                "--session",
                sessions_by_ticket["ticket-001"],
            )
        finally:
            worker.terminate()
            try:
                worker.wait(timeout=15)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)
            if sys.exc_info()[0] is not None:
                worker_log.flush()
                worker_log.seek(0)
                print(worker_log.read())
