"""Command-line entrypoint for the lab starter."""

import logging
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

logger = logging.getLogger(__name__)

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a minimal single-agent baseline that uses a real LLM call."""

    _init()
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)

    llm = LLMClient()

    system_prompt = (
        "You are a helpful research assistant. Given a research query, provide a comprehensive, "
        "well-structured response covering key findings, analysis, and conclusions. "
        "Write approximately 500 words in markdown format."
    )

    console.print(Panel("Running single-agent baseline...", style="blue"))

    try:
        response = llm.complete(system_prompt, query)
        state.final_answer = response.content
        console.print(Panel.fit(state.final_answer, title="Single-Agent Baseline"))

        if response.input_tokens or response.output_tokens:
            console.print(
                f"\n[dim]Tokens: in={response.input_tokens}, out={response.output_tokens}, "
                f"cost=${response.cost_usd:.6f}[/dim]"
                if response.cost_usd else
                f"\n[dim]Tokens: in={response.input_tokens}, out={response.output_tokens}[/dim]"
            )
    except Exception as exc:
        console.print(Panel.fit(f"Baseline failed: {exc}", title="Error", style="red"))
        raise typer.Exit(code=1) from exc


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow."""

    _init()
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()

    console.print(Panel("Running multi-agent workflow...", style="blue"))

    try:
        result = workflow.run(state)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc
    except Exception as exc:
        console.print(Panel.fit(f"Workflow failed: {exc}", title="Error", style="red"))
        raise typer.Exit(code=1) from exc

    # Display results
    if result.final_answer:
        console.print(Panel.fit(result.final_answer, title="Multi-Agent Result"))

    # Display trace summary
    if result.route_history:
        console.print(f"\n[bold]Route history:[/bold] {' → '.join(result.route_history)}")
        console.print(f"[bold]Iterations:[/bold] {result.iteration}")

    if result.errors:
        for err in result.errors:
            console.print(f"[red]Error: {err}[/red]")


@app.command()
def benchmark(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    output: Annotated[str, typer.Option("--output", "-o", help="Report output path")] = "benchmark_report.md",
) -> None:
    """Run benchmark comparing single-agent vs multi-agent."""

    _init()

    console.print(Panel("Running benchmark: single-agent vs multi-agent...", style="blue"))

    def _run_baseline(q: str) -> ResearchState:
        llm = LLMClient()
        st = ResearchState(request=ResearchQuery(query=q))
        resp = llm.complete(
            "You are a research assistant. Provide a comprehensive response in markdown.",
            q,
        )
        st.final_answer = resp.content
        return st

    def _run_multi(q: str) -> ResearchState:
        st = ResearchState(request=ResearchQuery(query=q))
        wf = MultiAgentWorkflow()
        return wf.run(st)

    # Run both approaches
    _, baseline_metrics = run_benchmark("single-agent-baseline", query, _run_baseline)
    _, multi_metrics = run_benchmark("multi-agent-workflow", query, _run_multi)

    # Render report
    report_md = render_markdown_report([baseline_metrics, multi_metrics])

    # Save report
    store = LocalArtifactStore()
    path = store.write_text(output, report_md)
    console.print(f"\n[green]Report saved to: {path}[/green]")

    # Display summary table
    table = Table(title="Benchmark Summary")
    table.add_column("Run", style="cyan")
    table.add_column("Latency (s)", justify="right")
    table.add_column("Cost (USD)", justify="right")
    table.add_column("Quality", justify="right")

    for m in [baseline_metrics, multi_metrics]:
        table.add_row(
            m.run_name,
            f"{m.latency_seconds:.2f}",
            f"${m.estimated_cost_usd:.6f}" if m.estimated_cost_usd else "N/A",
            f"{m.quality_score:.1f}" if m.quality_score else "N/A",
        )

    console.print(table)


if __name__ == "__main__":
    app()
