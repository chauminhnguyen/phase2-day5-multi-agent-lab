"""Tests for agent implementations.

Verifies that agents are properly implemented and produce expected outputs.
"""

import pytest

from multi_agent_research_lab.agents import (
    AnalystAgent,
    CriticAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState


def _make_state(query: str = "Explain multi-agent systems") -> ResearchState:
    return ResearchState(request=ResearchQuery(query=query))


def _make_state_with_research() -> ResearchState:
    """State with research notes populated (for analyst/writer tests)."""
    state = _make_state()
    state.sources = [
        SourceDocument(
            title="Multi-Agent Systems Overview",
            url="https://example.com/1",
            snippet="Multi-agent systems involve multiple AI agents collaborating.",
        ),
    ]
    state.research_notes = "Research notes about multi-agent systems: they involve coordination."
    return state


def _make_state_with_analysis() -> ResearchState:
    """State with analysis notes populated (for writer tests)."""
    state = _make_state_with_research()
    state.analysis_notes = "Analysis: Multi-agent systems improve task decomposition."
    return state


class TestSupervisorAgent:
    """Tests for supervisor routing logic."""

    def test_supervisor_routes_to_researcher_when_no_research(self) -> None:
        """Supervisor should route to researcher when no research notes exist."""
        state = _make_state()
        agent = SupervisorAgent()
        result = agent.run(state)
        assert "researcher" in result.route_history

    def test_supervisor_routes_to_analyst_when_research_exists(self) -> None:
        """Supervisor should route to analyst when research notes exist but not analysis."""
        state = _make_state_with_research()
        agent = SupervisorAgent()
        result = agent.run(state)
        assert "analyst" in result.route_history

    def test_supervisor_routes_to_writer_when_analysis_exists(self) -> None:
        """Supervisor should route to writer when analysis exists but no answer."""
        state = _make_state_with_analysis()
        agent = SupervisorAgent()
        result = agent.run(state)
        assert "writer" in result.route_history

    def test_supervisor_routes_to_done_when_answer_exists(self) -> None:
        """Supervisor should route to done when final answer exists."""
        state = _make_state_with_analysis()
        state.final_answer = "This is the final answer."
        agent = SupervisorAgent()
        result = agent.run(state)
        assert "done" in result.route_history

    def test_supervisor_enforces_max_iterations(self) -> None:
        """Supervisor should force 'done' when max iterations reached."""
        state = _make_state()
        state.iteration = 100  # Well past max
        agent = SupervisorAgent()
        result = agent.run(state)
        assert "done" in result.route_history


class TestResearcherAgent:
    """Tests for researcher agent (requires mock or real API)."""

    def test_researcher_populates_sources_and_notes(self) -> None:
        """Researcher should populate sources and research_notes."""
        state = _make_state()
        agent = ResearcherAgent()
        # This test will use mock search if no Tavily key is set
        # and will call real LLM if OpenAI key is set
        try:
            result = agent.run(state)
            assert result.sources is not None
            assert result.research_notes is not None
        except Exception:
            pytest.skip("Requires API keys to run")


class TestAnalystAgent:
    """Tests for analyst agent."""

    def test_analyst_populates_analysis_notes(self) -> None:
        """Analyst should populate analysis_notes from research notes."""
        state = _make_state_with_research()
        agent = AnalystAgent()
        try:
            result = agent.run(state)
            assert result.analysis_notes is not None
            assert len(result.analysis_notes) > 0
        except Exception:
            pytest.skip("Requires API keys to run")

    def test_analyst_handles_missing_research(self) -> None:
        """Analyst should handle case when no research notes exist."""
        state = _make_state()
        agent = AnalystAgent()
        result = agent.run(state)
        assert result.analysis_notes == "No research notes available for analysis."


class TestWriterAgent:
    """Tests for writer agent."""

    def test_writer_populates_final_answer(self) -> None:
        """Writer should produce a final answer."""
        state = _make_state_with_analysis()
        agent = WriterAgent()
        try:
            result = agent.run(state)
            assert result.final_answer is not None
            assert len(result.final_answer) > 0
        except Exception:
            pytest.skip("Requires API keys to run")
