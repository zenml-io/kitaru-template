"""Repository-level contracts for the standalone Kitaru template."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_public_template_contract_is_root_local() -> None:
    """Keep the public clone and runtime rooted in this repository."""
    assert (ROOT / "returns_agent").is_dir()
    assert (ROOT / "traces" / "langfuse-traces.jsonl").is_file()
    assert (ROOT / "scripts" / "run_ci_e2e.py").is_file()
    assert not (ROOT / "tests" / "canonical_returns_agent.py").exists()
    assert not (ROOT / "examples").exists()


def test_readme_owns_setup_without_copying_the_tutorial() -> None:
    """Keep setup executable here and the teaching walkthrough in Kitaru."""
    readme = (ROOT / "README.md").read_text()
    assert "git clone https://github.com/zenml-io/kitaru-template.git" in readme
    assert "traces/langfuse-traces.jsonl" in readme
    assert "kitaru-guided-tour" in readme
    assert "change returns_agent/agent.py" in readme
    assert "Experiment candidates come from changes" in readme
    assert "docs/book/tutorials/returns-agent" in readme
    assert "examples/pydantic_ai_ticket_resolver" not in readme
    assert "If the selected server is healthy, keep using it" in readme
    assert "If no usable server is selected" in readme
    assert readme.index("kitaru status") < readme.index("kitaru login --local")
    assert "paid model calls" not in readme
    assert readme.index("kitaru worker start") < readme.index("kitaru session import")
    assert len(readme.splitlines()) < 180


def test_development_checks_are_locked_with_the_template() -> None:
    """Keep standalone validation available from the frozen environment."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    development = project["dependency-groups"]["dev"]
    assert any(item.startswith("pytest") for item in development)
    assert any(item.startswith("ruff") for item in development)


def test_public_pull_request_ci_is_read_only_and_secretless() -> None:
    """Run fork-authored code without a privileged workflow trigger."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "permissions:\n  contents: read" in workflow
    assert "pull_request:" in workflow
    assert "pull_request_target" not in workflow
    assert "secrets." not in workflow
    assert "scripts/run_ci_e2e.py" in workflow


def test_local_kitaru_state_is_ignored() -> None:
    """Keep generated investigation state out of the public template."""
    ignores = (ROOT / ".gitignore").read_text().splitlines()
    assert ".kitaru/" in ignores
    assert ".zen/" in ignores
    assert "evaluator.py" in ignores
