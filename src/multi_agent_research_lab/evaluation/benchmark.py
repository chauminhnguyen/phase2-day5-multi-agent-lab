"""Benchmark skeleton for single-agent vs multi-agent.

Measures latency, estimates token cost, computes quality scores,
and tracks citation coverage and error rates.
"""

import logging
from time import perf_counter
from typing import Callable

from multi_agent_research_lab.core.schemas import AgentName, BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)

Runner = Callable[[str], ResearchState]


def _estimate_total_cost(state: ResearchState) -> float | None:
    """Sum up costs from all agent results."""
    total = 0.0
    found_any = False
    for result in state.agent_results:
        cost = result.metadata.get("cost_usd")
        if cost is not None:
            total += cost
            found_any = True
    return total if found_any else None


def _compute_quality_score(state: ResearchState) -> float | None:
    """Compute a heuristic quality score (0-10) based on output characteristics.

    Scoring criteria:
    - Has final answer (2 pts)
    - Answer length adequate ≥200 chars (2 pts)
    - Has sources (1 pt)
    - Number of sources ≥3 (1 pt)
    - Has research notes (1 pt)
    - Has analysis notes (1 pt)
    - No errors (1 pt)
    - Has citations/references in answer (1 pt)
    """

    if not state.final_answer:
        return 0.0

    score = 0.0

    # Has final answer
    score += 2.0

    # Adequate length
    if len(state.final_answer) >= 200:
        score += 2.0
    elif len(state.final_answer) >= 100:
        score += 1.0

    # Has sources
    if state.sources:
        score += 1.0
        if len(state.sources) >= 3:
            score += 1.0

    # Has research notes
    if state.research_notes:
        score += 1.0

    # Has analysis notes
    if state.analysis_notes:
        score += 1.0

    # No errors
    if not state.errors:
        score += 1.0

    # Has citations (check for markdown links or source references)
    answer_lower = state.final_answer.lower()
    if any(indicator in answer_lower for indicator in ["[", "source", "reference", "citation", "according to"]):
        score += 1.0

    return min(score, 10.0)


def _compute_citation_coverage(state: ResearchState) -> float | None:
    """Estimate what fraction of sources are cited in the final answer."""
    if not state.final_answer or not state.sources:
        return None

    answer_lower = state.final_answer.lower()
    cited = sum(
        1 for src in state.sources
        if src.title.lower()[:20] in answer_lower or (src.url and src.url in state.final_answer)
    )
    return cited / len(state.sources) if state.sources else None


def run_benchmark(run_name: str, query: str, runner: Runner) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency, cost, quality, and return comprehensive metrics.

    Includes quality scoring, estimated token cost, citation coverage, and error rate.
    """

    logger.info("Starting benchmark run: %s", run_name)
    started = perf_counter()

    try:
        state = runner(query)
        latency = perf_counter() - started
        has_error = False
    except Exception as exc:
        latency = perf_counter() - started
        logger.error("Benchmark run '%s' failed: %s", run_name, exc)
        state = ResearchState(
            request=__import__("multi_agent_research_lab.core.schemas", fromlist=["ResearchQuery"]).ResearchQuery(query=query)
        )
        state.errors.append(str(exc))
        has_error = True

    # Compute metrics
    cost = _estimate_total_cost(state)
    quality = _compute_quality_score(state)
    citation_cov = _compute_citation_coverage(state)

    # Build notes
    notes_parts: list[str] = []
    if state.iteration > 0:
        notes_parts.append(f"iterations={state.iteration}")
    if state.sources:
        notes_parts.append(f"sources={len(state.sources)}")
    if citation_cov is not None:
        notes_parts.append(f"citation_coverage={citation_cov:.0%}")
    if state.errors:
        notes_parts.append(f"errors={len(state.errors)}")
    if has_error:
        notes_parts.append("FAILED")

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=cost,
        quality_score=quality,
        notes="; ".join(notes_parts),
    )

    logger.info(
        "Benchmark '%s': latency=%.2fs cost=$%s quality=%s",
        run_name,
        latency,
        f"{cost:.6f}" if cost else "N/A",
        f"{quality:.1f}" if quality else "N/A",
    )

    return state, metrics
