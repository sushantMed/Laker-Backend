"""
Observability: Tracing
-----------------------
Stub that mirrors the OpenTelemetry span API.
Replace body with `opentelemetry-sdk` for production.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

logger = logging.getLogger("laker.trace")


@contextmanager
def start_span(
    name: str, attributes: dict | None = None
) -> Generator[None, None, None]:
    logger.debug("SPAN start  name=%s  attrs=%s", name, attributes)
    try:
        yield
    finally:
        logger.debug("SPAN end    name=%s", name)
