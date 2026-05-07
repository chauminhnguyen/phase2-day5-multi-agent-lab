# Trace Documentation

## LangSmith Trace Link

Multi-agent workflow traces are available at:

**Dashboard URL**: https://smith.langchain.com/

## How to Access Traces

1. Navigate to [LangSmith](https://smith.langchain.com/)
2. Select the project `multi_agent_research_lab`
3. View traces under the "Traces" tab

## Trace Events Captured

The benchmark run captured the following trace events:

```
2026-05-06 13:19:56,715 - multi_agent_workflow started
2026-05-06 13:19:56,911 - Iteration 1: supervisor → researcher (Tavily search)
2026-05-06 13:20:12,778 - Iteration 2: supervisor → analyst
2026-05-06 13:20:39,741 - Iteration 3: supervisor → writer
2026-05-06 13:20:39,744 - Workflow complete (4 iterations)
```

## Langfuse Trace Link

For additional tracing via Langfuse:

**Langfuse Dashboard**: https://cloud.langfuse.com

Note: Configure your `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in `.env` to enable Langfuse tracing.

## Screenshot

[Screenshot of LangSmith trace will be captured during the benchmark run]

![LangSmith Trace Screenshot](trace_screenshot.png)
