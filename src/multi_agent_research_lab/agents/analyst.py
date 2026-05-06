"""Analyst agent.

Extracts key claims, compares viewpoints, flags weak evidence,
and produces structured analysis notes.
"""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """You are a critical analyst for a research system. Given research notes,
perform a thorough analysis.

Your analysis should:
1. Extract the top key claims or findings.
2. Evaluate the strength of evidence for each claim (strong/moderate/weak).
3. Identify contradictions or disagreements between sources.
4. Flag any potential biases or gaps in the research.
5. Provide a structured summary of insights.
6. Rate the overall confidence level of the research (high/medium/low).

Format your response as structured markdown with clear sections."""


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self) -> None:
        self._llm = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`.

        Extracts key claims, compares viewpoints, and flags weak evidence.
        """

        with trace_span("analyst_run", {"has_research": bool(state.research_notes)}) as span:
            if not state.research_notes:
                state.analysis_notes = "No research notes available for analysis."
                logger.warning("Analyst invoked without research notes.")
                return state

            source_context = ""
            if state.sources:
                source_context = "\n\nOriginal sources:\n" + "\n".join(
                    f"- [{src.title}]({src.url})" if src.url else f"- {src.title}"
                    for src in state.sources
                )

            user_prompt = (
                f"Research query: {state.request.query}\n"
                f"Target audience: {state.request.audience}\n\n"
                f"Research notes:\n{state.research_notes}"
                f"{source_context}\n\n"
                f"Please perform a critical analysis of these research findings."
            )

            try:
                response = self._llm.complete(ANALYSIS_SYSTEM_PROMPT, user_prompt)
                state.analysis_notes = response.content

                state.agent_results.append(
                    AgentResult(
                        agent=AgentName.ANALYST,
                        content=response.content,
                        metadata={
                            "input_tokens": response.input_tokens,
                            "output_tokens": response.output_tokens,
                            "cost_usd": response.cost_usd,
                        },
                    )
                )
            except Exception as exc:
                logger.error("Analyst LLM failed: %s", exc)
                state.errors.append(f"Analyst LLM error: {exc}")
                # Fallback: pass research notes as analysis
                state.analysis_notes = (
                    f"## Auto-generated Analysis\n\n"
                    f"LLM analysis failed. Raw research notes:\n\n{state.research_notes}"
                )

            state.add_trace_event("analyst_complete", {
                "notes_length": len(state.analysis_notes) if state.analysis_notes else 0,
            })
            span["analysis_length"] = len(state.analysis_notes) if state.analysis_notes else 0

        return state
