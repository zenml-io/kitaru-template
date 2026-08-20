"""PydanticAI returns resolver run directly or by a Kitaru worker."""

import asyncio
import json
import os
from decimal import Decimal
from typing import Any, cast

from kitaru.task import get_task_inputs as get_kitaru_task_inputs
from kitaru_pydantic_ai import KitaruAgent
from pydantic_ai import Agent
from pydantic_ai.models import KnownModelName, Model

from returns_agent.models import Resolution, TicketInput
from returns_agent.store import MockCommerceStore

MODEL: KnownModelName = "openai:gpt-5-nano"

_TASK_INSTRUCTIONS = (
    "You autonomously resolve one customer return or delivery ticket.\n\n"
    "Investigate the ticket with the available tools, choose one terminal "
    "outcome, execute any refund, replacement, or escalation before replying, "
    "then return the structured resolution. Use lookup_order before making "
    "claims about an order. Use get_return_policy for return or refund "
    "decisions. Use check_shipping for delivery problems.\n\n"
)

_BASELINE_POLICY = (
    "Prioritize a fast, generous resolution. Customer-reported defects usually "
    "receive a full refund. Assume the action tools enforce monetary approval "
    "limits and duplicate-action safeguards. Escalate when the order cannot be "
    "identified or no supported resolution is available.\n\n"
)

_REPLY_INSTRUCTIONS = (
    "The customer reply must accurately describe the accepted tool action. "
    "Address the customer by first name. Do not expose email addresses, "
    "internal risk flags, or mock receipt identifiers. All records and actions "
    "in this example are synthetic."
)

INSTRUCTIONS = _TASK_INSTRUCTIONS + _BASELINE_POLICY + _REPLY_INSTRUCTIONS


def get_instructions() -> str:
    """Build the resolver instructions."""
    return INSTRUCTIONS


def get_ticket_input(value: Any) -> TicketInput:
    """Unwrap the latest imported turn into one ticket input."""
    if isinstance(value, dict) and isinstance(value.get("turns"), list):
        turns = value["turns"]
        if not turns:
            raise ValueError("The imported session has no turns.")
        value = turns[-1].get("inputs")
    return TicketInput.model_validate(value)


def get_runtime_inputs() -> Any:
    """Read task inputs from an external evaluator or a Kitaru worker."""
    inputs = os.environ.get("KITARU_TASK_INPUTS")
    if inputs is not None:
        return json.loads(inputs)
    return get_kitaru_task_inputs()


def get_runtime_model() -> KnownModelName:
    """Use an evaluator-selected model or the example default."""
    return cast(KnownModelName, os.environ.get("OPENAI_MODEL", MODEL))


def build_prompt(ticket: TicketInput) -> str:
    """Render one incoming email without adding hidden case labels."""
    return (
        f"Ticket: {ticket.ticket_id}\n"
        f"From: {ticket.customer_name} <{ticket.email}>\n"
        f"Subject: {ticket.subject}\n\n"
        f"{ticket.body}"
    )


def build_agent(
    store: MockCommerceStore,
    model: Model | KnownModelName = MODEL,
) -> Agent[None, Resolution]:
    """Build the baseline resolver around one isolated mock store."""
    agent = Agent[None, Resolution](
        model,
        output_type=Resolution,
        instructions=get_instructions(),
        retries=2,
        model_settings={"openai_reasoning_summary": "auto"},
    )

    @agent.tool_plain
    def lookup_order(
        order_id: str | None = None, email: str | None = None
    ) -> dict[str, Any]:
        """Look up an order by exact order number or customer email."""
        return store.lookup_order(order_id, email).model_dump(mode="json")

    @agent.tool_plain
    def get_return_policy(category: str) -> dict[str, Any]:
        """Get the return window, defect rules, final-sale rule, and approval limit."""
        return store.get_return_policy(category).model_dump(mode="json")

    @agent.tool_plain
    def check_shipping(tracking_no: str) -> dict[str, Any]:
        """Check carrier status for a shipped or missing order."""
        return store.check_shipping(tracking_no).model_dump(mode="json")

    @agent.tool_plain
    def issue_refund(order_id: str, amount: Decimal) -> dict[str, Any]:
        """Record a mock refund; no payment processor is contacted."""
        return store.issue_refund(order_id, amount).model_dump(mode="json")

    @agent.tool_plain
    def create_replacement(order_id: str) -> dict[str, Any]:
        """Record a mock replacement; no fulfillment order is created."""
        return store.create_replacement(order_id).model_dump(mode="json")

    @agent.tool_plain
    def escalate_to_human(reason: str) -> dict[str, Any]:
        """Record a mock escalation with a concise internal reason."""
        return store.escalate_to_human(reason).model_dump(mode="json")

    return agent


async def main() -> None:
    """Resolve one replayed ticket in the selected execution mode."""
    ticket = get_ticket_input(get_runtime_inputs())
    pydantic_agent = build_agent(MockCommerceStore(), get_runtime_model())
    prompt = build_prompt(ticket)
    if os.environ.get("KITARU_EXTERNAL_EVALUATION") == "1":
        result = await pydantic_agent.run(prompt)
        print(result.output.model_dump_json())
        return

    agent = KitaruAgent(
        pydantic_agent,
        session_name=f"Returns ticket: {ticket.ticket_id}",
    )
    result = await agent.run(prompt)
    print(result.output.model_dump_json())


if __name__ == "__main__":
    asyncio.run(main())
