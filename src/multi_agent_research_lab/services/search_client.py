"""Search client abstraction for ResearcherAgent."""

import logging

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


class SearchClient:
    """Provider-agnostic search client with Tavily integration and mock fallback."""

    def __init__(self) -> None:
        settings = get_settings()
        self._tavily_key = settings.tavily_api_key

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query.

        Uses Tavily API if key is available, otherwise falls back to a mock.
        """

        if self._tavily_key:
            return self._tavily_search(query, max_results)
        logger.warning("No TAVILY_API_KEY configured – using mock search results.")
        return self._mock_search(query, max_results)

    def _tavily_search(self, query: str, max_results: int) -> list[SourceDocument]:
        """Search using Tavily API."""
        from tavily import TavilyClient

        logger.info("SearchClient.search via Tavily query=%r max=%d", query[:80], max_results)
        client = TavilyClient(api_key=self._tavily_key)
        response = client.search(query=query, max_results=max_results, search_depth="advanced")

        docs: list[SourceDocument] = []
        for result in response.get("results", []):
            docs.append(
                SourceDocument(
                    title=result.get("title", "Untitled"),
                    url=result.get("url"),
                    snippet=result.get("content", ""),
                    metadata={"score": result.get("score", 0)},
                )
            )
        logger.info("SearchClient returned %d sources", len(docs))
        return docs

    @staticmethod
    def _mock_search(query: str, max_results: int) -> list[SourceDocument]:
        """Return synthetic results for offline development."""
        mock_results = [
            SourceDocument(
                title=f"Mock Source {i + 1}: {query[:40]}",
                url=f"https://example.com/article-{i + 1}",
                snippet=(
                    f"This is a mock search result {i + 1} providing relevant information about "
                    f"'{query[:60]}'. It contains key findings, data points, and expert analysis "
                    f"that can be used for research purposes."
                ),
                metadata={"mock": True, "score": round(0.95 - i * 0.1, 2)},
            )
            for i in range(min(max_results, 5))
        ]
        return mock_results
