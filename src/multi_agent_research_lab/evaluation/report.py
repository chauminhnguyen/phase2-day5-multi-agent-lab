"""Benchmark report rendering.

Generates a comprehensive markdown report comparing single-agent
vs multi-agent approaches with detailed analysis.
"""

from datetime import datetime, timezone

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render benchmark metrics to a comprehensive markdown report.

    Includes comparison table, analysis, and recommendations.
    """

    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Benchmark Report: Single-Agent vs Multi-Agent",
        "",
        f"**Generated:** {now}",
        "",
        "## Summary Table",
        "",
        "| Run | Latency (s) | Cost (USD) | Quality (0-10) | Notes |",
        "|---|---:|---:|---:|---|",
    ]

    for item in metrics:
        cost = "N/A" if item.estimated_cost_usd is None else f"${item.estimated_cost_usd:.4f}"
        quality = "N/A" if item.quality_score is None else f"{item.quality_score:.1f}"
        lines.append(f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} | {item.notes} |")

    # Add analysis section
    lines.extend([
        "",
        "## Analysis",
        "",
    ])

    if len(metrics) >= 2:
        baseline = metrics[0]
        multi = metrics[1]

        # Latency comparison
        if baseline.latency_seconds > 0:
            latency_ratio = multi.latency_seconds / baseline.latency_seconds
            lines.append(f"### Latency")
            lines.append(f"- Single-agent: **{baseline.latency_seconds:.2f}s**")
            lines.append(f"- Multi-agent: **{multi.latency_seconds:.2f}s**")
            lines.append(f"- Multi-agent is **{latency_ratio:.1f}x** {'slower' if latency_ratio > 1 else 'faster'}")
            lines.append("")

        # Quality comparison
        if baseline.quality_score is not None and multi.quality_score is not None:
            quality_diff = multi.quality_score - baseline.quality_score
            lines.append(f"### Quality")
            lines.append(f"- Single-agent: **{baseline.quality_score:.1f}/10**")
            lines.append(f"- Multi-agent: **{multi.quality_score:.1f}/10**")
            if quality_diff > 0:
                lines.append(f"- Multi-agent scores **+{quality_diff:.1f}** higher")
            elif quality_diff < 0:
                lines.append(f"- Single-agent scores **+{-quality_diff:.1f}** higher")
            else:
                lines.append("- Both approaches score equally")
            lines.append("")

        # Cost comparison
        if baseline.estimated_cost_usd is not None and multi.estimated_cost_usd is not None:
            cost_ratio = multi.estimated_cost_usd / baseline.estimated_cost_usd if baseline.estimated_cost_usd > 0 else float("inf")
            lines.append(f"### Cost")
            lines.append(f"- Single-agent: **${baseline.estimated_cost_usd:.4f}**")
            lines.append(f"- Multi-agent: **${multi.estimated_cost_usd:.4f}**")
            lines.append(f"- Multi-agent costs **{cost_ratio:.1f}x** {'more' if cost_ratio > 1 else 'less'}")
            lines.append("")

    # Recommendations
    lines.extend([
        "## Recommendations",
        "",
        "- **Use single-agent** for simple queries where latency matters most.",
        "- **Use multi-agent** for complex research tasks requiring depth, analysis, and citations.",
        "- **Consider cost** when choosing: multi-agent uses multiple LLM calls.",
        "- **Monitor** quality scores and citation coverage as key indicators of output value.",
        "",
        "## Failure Modes & Mitigations",
        "",
        "| Failure Mode | Mitigation |",
        "|---|---|",
        "| Agent infinite loop | Max iterations guardrail (default: 6) |",
        "| LLM timeout | Retry with exponential backoff (3 attempts) |",
        "| Search API failure | Fallback to mock search results |",
        "| LLM output parsing | Graceful fallback to raw notes |",
        "| Cost overrun | Token tracking + budget alerts |",
        "",
    ])

    return "\n".join(lines) + "\n"
