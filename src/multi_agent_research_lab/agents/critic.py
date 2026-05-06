"""Optional critic agent for fact-checking and quality review.

Validates the final answer for accuracy, citation coverage,
and potential hallucinations.
"""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

CRITIC_SYSTEM_PROMPT = """You are a fact-checker and quality reviewer for a research system.
Given the final answer and the original sources, evaluate the response.

Check for:
1. **Factual accuracy**: Are claims supported by the sources?
2. **Citation coverage**: Are key claims properly attributed?
3. **Hallucination risk**: Are there claims not grounded in any source?
4. **Completeness**: Does the response adequately address the original query?
5. **Clarity**: Is the response well-structured and easy to understand?

Provide a structured review with:
- Overall quality score (1-10)
- List of issues found (if any)
- Suggestions for improvement
- Verdict: PASS or NEEDS_REVISION

Format your response as structured markdown."""


class CriticAgent(BaseAgent):
    """Optional fact-checking and safety-review agent."""

    name = "critic"

    def __init__(self) -> None:
        self._llm = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final answer and append findings.

        Performs fact-check, citation coverage, and hallucination checks.
        """

        with trace_span("critic_run", {"has_answer": bool(state.final_answer)}) as span:
            if not state.final_answer:
                logger.warning("Critic invoked without a final answer.")
                return state

            source_context = ""
            if state.sources:
                source_context = "\n\nOriginal sources:\n" + "\n".join(
                    f"- {src.title}: {src.snippet[:200]}"
                    for src in state.sources
                )

            user_prompt = (
                f"Original query: {state.request.query}\n\n"
                f"Final answer to review:\n{state.final_answer}\n"
                f"{source_context}\n\n"
                f"Please review this response for accuracy and quality."
            )

            try:
                response = self._llm.complete(CRITIC_SYSTEM_PROMPT, user_prompt)

                state.agent_results.append(
                    AgentResult(
                        agent=AgentName.CRITIC,
                        content=response.content,
                        metadata={
                            "input_tokens": response.input_tokens,
                            "output_tokens": response.output_tokens,
                            "cost_usd": response.cost_usd,
                        },
                    )
                )

                state.add_trace_event("critic_review", {
                    "review_length": len(response.content),
                })
                span["review_length"] = len(response.content)

            except Exception as exc:
                logger.error("Critic LLM failed: %s", exc)
                state.errors.append(f"Critic LLM error: {exc}")

        return state
