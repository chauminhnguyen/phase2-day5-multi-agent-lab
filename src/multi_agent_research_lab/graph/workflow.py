"""LangGraph workflow for multi-agent orchestration.

Builds a state graph with supervisor routing, worker agent nodes,
conditional edges, and stop conditions.
"""

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.critic import CriticAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span

logger = logging.getLogger(__name__)


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self) -> None:
        self._supervisor = SupervisorAgent()
        self._researcher = ResearcherAgent()
        self._analyst = AnalystAgent()
        self._writer = WriterAgent()
        self._critic = CriticAgent()
        self._settings = get_settings()

    # ── Node functions ──────────────────────────────────────────────

    def _supervisor_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the supervisor to decide next route."""
        rs = ResearchState(**state)
        rs = self._supervisor.run(rs)
        return rs.model_dump()

    def _researcher_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the researcher agent."""
        rs = ResearchState(**state)
        rs = self._researcher.run(rs)
        return rs.model_dump()

    def _analyst_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the analyst agent."""
        rs = ResearchState(**state)
        rs = self._analyst.run(rs)
        return rs.model_dump()

    def _writer_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the writer agent."""
        rs = ResearchState(**state)
        rs = self._writer.run(rs)
        return rs.model_dump()

    def _critic_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the optional critic agent."""
        rs = ResearchState(**state)
        rs = self._critic.run(rs)
        return rs.model_dump()

    # ── Routing logic ───────────────────────────────────────────────

    @staticmethod
    def _route_after_supervisor(state: dict[str, Any]) -> str:
        """Conditional routing based on supervisor's last route decision."""
        route_history = state.get("route_history", [])
        if not route_history:
            return END

        last_route = route_history[-1]
        route_map = {
            "researcher": "researcher",
            "analyst": "analyst",
            "writer": "writer",
            "done": END,
        }
        return route_map.get(last_route, END)

    # ── Build & Run ─────────────────────────────────────────────────

    def build(self) -> StateGraph:
        """Create a LangGraph state graph.

        Nodes: supervisor, researcher, analyst, writer, critic (optional).
        Edges: supervisor → conditional route → worker → supervisor (loop).
        Stop condition: supervisor routes to "done" or max iterations reached.
        """

        graph = StateGraph(dict)

        # Add nodes
        graph.add_node("supervisor", self._supervisor_node)
        graph.add_node("researcher", self._researcher_node)
        graph.add_node("analyst", self._analyst_node)
        graph.add_node("writer", self._writer_node)

        # Set entry point
        graph.set_entry_point("supervisor")

        # Conditional routing from supervisor
        graph.add_conditional_edges(
            "supervisor",
            self._route_after_supervisor,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                END: END,
            },
        )

        # Workers always loop back to supervisor
        graph.add_edge("researcher", "supervisor")
        graph.add_edge("analyst", "supervisor")
        graph.add_edge("writer", "supervisor")

        return graph

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state.

        Compiles the graph, invokes it, and converts result back to ResearchState.
        """

        with trace_span("multi_agent_workflow", {"query": state.request.query}) as span:
            logger.info("Starting multi-agent workflow for query: %s", state.request.query[:80])

            # Build and compile the graph
            graph = self.build()
            compiled = graph.compile()

            # Convert state to dict for LangGraph
            initial_state = state.model_dump()

            # Run the graph
            try:
                final_state_dict = compiled.invoke(
                    initial_state,
                    config={"recursion_limit": self._settings.max_iterations * 3},
                )
            except Exception as exc:
                logger.error("Workflow execution failed: %s", exc)
                state.errors.append(f"Workflow error: {exc}")
                state.final_answer = (
                    f"Workflow failed with error: {exc}. "
                    f"Partial results may be available in agent_results."
                )
                return state

            # Convert back to ResearchState
            result = ResearchState(**final_state_dict)

            span["iterations"] = result.iteration
            span["has_answer"] = bool(result.final_answer)
            logger.info(
                "Workflow complete: %d iterations, answer=%s",
                result.iteration,
                "yes" if result.final_answer else "no",
            )

        return result
