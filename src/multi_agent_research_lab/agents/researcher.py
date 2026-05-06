"""Researcher agent.

Searches for sources relevant to the query, captures citations,
and compiles concise research notes.
"""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = """You are a thorough research assistant. Given a query and a set of
source documents, create comprehensive research notes.

Your notes should:
1. Summarize the key findings from each source.
2. Identify agreements and disagreements between sources.
3. Note the credibility/relevance of each source.
4. Cite sources by their title when making claims.
5. Highlight any gaps in the available information.

Format your response as structured markdown notes."""


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self) -> None:
        self._llm = LLMClient()
        self._search = SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`.

        Implements search, source filtering, citation capture, and notes synthesis.
        """

        with trace_span("researcher_run", {"query": state.request.query}) as span:
            # Step 1: Search for sources
            try:
                sources = self._search.search(
                    query=state.request.query,
                    max_results=state.request.max_sources,
                )
                state.sources = sources
                logger.info("Researcher found %d sources", len(sources))
            except Exception as exc:
                logger.error("Search failed: %s", exc)
                state.errors.append(f"Researcher search error: {exc}")
                state.sources = []

            # Step 2: Synthesize research notes via LLM
            if state.sources:
                source_text = "\n\n".join(
                    f"### Source {i + 1}: {src.title}\n"
                    f"URL: {src.url or 'N/A'}\n"
                    f"Content: {src.snippet}"
                    for i, src in enumerate(state.sources)
                )
                user_prompt = (
                    f"Research query: {state.request.query}\n"
                    f"Target audience: {state.request.audience}\n\n"
                    f"Sources found:\n{source_text}\n\n"
                    f"Please create comprehensive research notes from these sources."
                )

                try:
                    response = self._llm.complete(RESEARCH_SYSTEM_PROMPT, user_prompt)
                    state.research_notes = response.content

                    state.agent_results.append(
                        AgentResult(
                            agent=AgentName.RESEARCHER,
                            content=response.content,
                            metadata={
                                "num_sources": len(state.sources),
                                "input_tokens": response.input_tokens,
                                "output_tokens": response.output_tokens,
                                "cost_usd": response.cost_usd,
                            },
                        )
                    )
                except Exception as exc:
                    logger.error("LLM synthesis failed: %s", exc)
                    state.errors.append(f"Researcher LLM error: {exc}")
                    # Fallback: use raw source snippets as notes
                    state.research_notes = source_text
            else:
                state.research_notes = (
                    f"No sources found for query: '{state.request.query}'. "
                    f"The research may need to be conducted with different search terms."
                )

            state.add_trace_event("researcher_complete", {
                "num_sources": len(state.sources),
                "notes_length": len(state.research_notes) if state.research_notes else 0,
            })
            span["num_sources"] = len(state.sources)

        return state
