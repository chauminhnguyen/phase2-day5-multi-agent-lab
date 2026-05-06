"""Supervisor / router agent.

Decides which worker should run next based on current state, enforces
max iterations, and handles failure fallback.
"""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

ROUTING_SYSTEM_PROMPT = """You are a routing supervisor for a multi-agent research system.
Your job is to decide which agent should run next based on the current progress.

Available agents:
- researcher: Searches for sources and creates research notes. Use when no research has been done yet.
- analyst: Analyzes research notes to extract key claims and insights. Use after research notes are ready.
- writer: Writes the final answer using research and analysis notes. Use after analysis is complete.
- done: The workflow is complete. Use when a final answer has been written.

Rules:
1. Always start with "researcher" if no research_notes exist.
2. Move to "analyst" once research_notes are populated.
3. Move to "writer" once analysis_notes are populated.
4. Return "done" once final_answer is populated.
5. Never repeat the same agent more than twice consecutively.
6. If you are unsure, default to "done" to prevent infinite loops.

Reply with ONLY one word: researcher, analyst, writer, or done."""


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self) -> None:
        self._llm = LLMClient()
        self._settings = get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route.

        Implements a routing policy that:
        - Inspects request, current notes, and missing fields.
        - Chooses one of: researcher, analyst, writer, done.
        - Enforces max iterations and failure fallback.
        """

        with trace_span("supervisor_route", {"iteration": state.iteration}) as span:
            # Guardrail: enforce max iterations
            if state.iteration >= self._settings.max_iterations:
                logger.warning("Max iterations (%d) reached – forcing done.", self._settings.max_iterations)
                route = "done"
            else:
                route = self._decide_route(state)

            state.record_route(route)
            state.add_trace_event("supervisor_decision", {
                "route": route,
                "iteration": state.iteration,
            })

            state.agent_results.append(
                AgentResult(
                    agent=AgentName.SUPERVISOR,
                    content=f"Routed to: {route}",
                    metadata={"iteration": state.iteration, "route": route},
                )
            )

            span["route"] = route
            logger.info("Supervisor decided: %s (iteration %d)", route, state.iteration)

        return state

    def _decide_route(self, state: ResearchState) -> str:
        """Determine next route using a rule-based policy with LLM fallback."""

        # Rule-based fast path
        if not state.research_notes:
            return "researcher"
        if not state.analysis_notes:
            return "analyst"
        if not state.final_answer:
            return "writer"
        if state.final_answer:
            return "done"

        # LLM fallback for ambiguous states
        try:
            context = (
                f"Query: {state.request.query}\n"
                f"Has research notes: {bool(state.research_notes)}\n"
                f"Has analysis notes: {bool(state.analysis_notes)}\n"
                f"Has final answer: {bool(state.final_answer)}\n"
                f"Current iteration: {state.iteration}\n"
                f"Route history: {state.route_history}"
            )
            response = self._llm.complete(ROUTING_SYSTEM_PROMPT, context)
            route = response.content.strip().lower()
            if route in ("researcher", "analyst", "writer", "done"):
                return route
        except Exception as exc:
            logger.error("LLM routing failed, falling back to 'done': %s", exc)
            state.errors.append(f"Supervisor LLM error: {exc}")

        return "done"
