"""
Observability: Metrics
-----------------------
Lightweight in-process counters/gauges.
In production replace with prometheus-fastapi-instrumentator or
opentelemetry-sdk.
"""

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class _Counter:
    value: int = 0

    def inc(self) -> None:
        self.value += 1


@dataclass
class _Histogram:
    samples: list[float] = field(default_factory=list)

    def observe(self, v: float) -> None:
        self.samples.append(v)

    def summary(self) -> dict:
        if not self.samples:
            return {}
        s = sorted(self.samples)
        n = len(s)
        return {
            "count": n,
            "p50": s[n // 2],
            "p95": s[int(n * 0.95)],
            "p99": s[int(n * 0.99)],
        }


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: dict[str, _Counter] = defaultdict(_Counter)
        self._histograms: dict[str, _Histogram] = defaultdict(_Histogram)

    def inc(self, name: str) -> None:
        self._counters[name].inc()

    def observe(self, name: str, value: float) -> None:
        self._histograms[name].observe(value)

    def snapshot(self) -> dict:
        return {
            "counters": {k: v.value for k, v in self._counters.items()},
            "histograms": {k: v.summary() for k, v in self._histograms.items()},
        }


registry = MetricsRegistry()
