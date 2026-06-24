from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class MetricProvider(Protocol):
    """Pre-processes a DataFrame before chart-generation runs.

    Implementations handle any per-metric dataframe transformation that must
    happen before MetricsEngine sees the data (e.g. evaluating a formula,
    enriching columns from raw JSON).
    """

    metric_code: str

    def prepare_dataframe(
        self,
        df: pd.DataFrame,
        analysis,
        dataset_service,
    ) -> pd.DataFrame:
        """Return a (possibly new) DataFrame ready for the MetricsEngine."""
        ...


class MetricProviderRegistry:
    """Thread-safe registry of MetricProvider instances keyed by metric_code."""

    def __init__(self) -> None:
        self._providers: dict[str, MetricProvider] = {}

    def register(self, provider: MetricProvider) -> None:
        self._providers[provider.metric_code] = provider

    def get(self, metric_code: str) -> MetricProvider | None:
        return self._providers.get(metric_code)

    def codes(self) -> list[str]:
        return list(self._providers.keys())


_registry = MetricProviderRegistry()


def register_provider(provider: MetricProvider) -> None:
    _registry.register(provider)


def get_provider(metric_code: str) -> MetricProvider | None:
    return _registry.get(metric_code)
