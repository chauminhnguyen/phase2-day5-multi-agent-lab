"""Writer agent.

Synthesizes research and analysis notes into a clear, well-structured
final response with proper citations.
"""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

WRITER_SYSTEM_PROMPT = """You are an expert research writer. Given research notes and analysis,
write a comprehensive, well-structured final response.

Your response should:
1. Open with a concise executive summary.
2. Present key findings in a logical order.
3. Include proper citations referencing the source titles.
4. Use clear headings and subheadings.
5. End with a conclusion and any remaining open questions.
6. Be written for the specified target audience.
7. Be approximately 500-800 words unless otherwise specified.

Format your response as clean, professional markdown."""


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self) -> None:
        self._llm = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`.

        Synthesizes a clear response with citations and source references.
        """

        with trace_span("writer_run", {
            "has_research": bool(state.research_notes),
            "has_analysis": bool(state.analysis_notes),
        }) as span:
            # Build comprehensive context for the writer
            context_parts: list[str] = [
                f"Original query: {state.request.query}",
                f"Target audience: {state.request.audience}",
            ]

            if state.research_notes:
                context_parts.append(f"\n## Research Notes\n{state.research_notes}")

            if state.analysis_notes:
                context_parts.append(f"\n## Analysis\n{state.analysis_notes}")

            if state.sources:
                source_refs = "\n".join(
                    f"- [{src.title}]({src.url})" if src.url else f"- {src.title}"
                    for src in state.sources
                )
                context_parts.append(f"\n## Available Sources\n{source_refs}")

            user_prompt = "\n".join(context_parts) + (
                "\n\nPlease write a comprehensive final response based on the above "
                "research and analysis. Include citations where appropriate."
            )

            try:
                response = self._llm.complete(WRITER_SYSTEM_PROMPT, user_prompt)
                state.final_answer = response.content

                state.agent_results.append(
                    AgentResult(
                        agent=AgentName.WRITER,
                        content=response.content,
                        metadata={
                            "input_tokens": response.input_tokens,
                            "output_tokens": response.output_tokens,
                            "cost_usd": response.cost_usd,
                        },
                    )
                )
            except Exception as exc:
                logger.error("Writer LLM failed: %s", exc)
                state.errors.append(f"Writer LLM error: {exc}")
                # Fallback: compile available notes as the answer
                state.final_answer = (
                    f"# {state.request.query}\n\n"
                    f"*Note: LLM writing failed. Below are the raw notes.*\n\n"
                    f"## Research Notes\n{state.research_notes or 'N/A'}\n\n"
                    f"## Analysis\n{state.analysis_notes or 'N/A'}"
                )

            state.add_trace_event("writer_complete", {
                "answer_length": len(state.final_answer) if state.final_answer else 0,
            })
            span["answer_length"] = len(state.final_answer) if state.final_answer else 0

        return state
