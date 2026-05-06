"""Tracing hooks.

Provides both a minimal span context and optional LangSmith/Langfuse integration.
Students can configure their preferred provider via environment variables.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any

logger = logging.getLogger(__name__)

# ── Optional provider integration ───────────────────────────────────

_langsmith_initialized = False
_langfuse_client = None


def _init_langsmith() -> bool:
    """Try to initialize LangSmith tracing if configured."""
    global _langsmith_initialized
    if _langsmith_initialized:
        return True
    try:
        import os
        if os.getenv("LANGSMITH_API_KEY"):
            os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
            os.environ.setdefault("LANGCHAIN_PROJECT", os.getenv("LANGSMITH_PROJECT", "multi-agent-research-lab"))
            _langsmith_initialized = True
            logger.info("LangSmith tracing enabled.")
            return True
    except Exception as exc:
        logger.debug("LangSmith init failed: %s", exc)
    return False


def _init_langfuse() -> Any:
    """Try to initialize Langfuse client if configured."""
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client
    try:
        import os
        if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
            from langfuse import Langfuse
            _langfuse_client = Langfuse()
            logger.info("Langfuse tracing enabled.")
            return _langfuse_client
    except Exception as exc:
        logger.debug("Langfuse init failed: %s", exc)
    return None


# ── Public tracing API ──────────────────────────────────────────────

@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Context manager that creates a trace span.

    Supports:
    - Local JSON spans (always active)
    - LangSmith spans (if LANGSMITH_API_KEY set)
    - Langfuse spans (if LANGFUSE_PUBLIC_KEY/SECRET_KEY set)
    """

    started = perf_counter()
    span: dict[str, Any] = {
        "name": name,
        "attributes": attributes or {},
        "duration_seconds": None,
        "status": "running",
    }

    # Try Langfuse span
    langfuse = _init_langfuse()
    langfuse_span = None
    if langfuse:
        try:
            langfuse_span = langfuse.trace(name=name, metadata=attributes or {})
        except Exception as exc:
            logger.debug("Langfuse trace creation failed: %s", exc)

    # Ensure LangSmith is initialized (it auto-traces via langchain)
    _init_langsmith()

    try:
        yield span
        span["status"] = "completed"
    except Exception as exc:
        span["status"] = "error"
        span["error"] = str(exc)
        raise
    finally:
        span["duration_seconds"] = perf_counter() - started

        # Log the span
        logger.debug(
            "Span[%s] duration=%.3fs status=%s attrs=%s",
            name,
            span["duration_seconds"],
            span["status"],
            span["attributes"],
        )

        # Flush Langfuse if available
        if langfuse:
            try:
                langfuse.flush()
            except Exception:
                pass
