import logging
import sys

from app.core.config import settings


def _build_formatter() -> logging.Formatter:
    if settings.is_production:
        # JSON-style single-line for log aggregators
        fmt = (
            '{"time":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","message":"%(message)s"}'
        )
    else:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    return logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S")


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_build_formatter())

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.app_debug else logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence chatty libraries
    for name in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
