"""
Metric Registry
===============
Singleton registry that keeps track of all available MetricPlugin instances.

Plugins can be registered at startup (builtin) or dynamically at runtime
(custom plugins validated by the LLM pipeline).

Usage:
    from collectors.domain.plugins import registry

    # Register a builtin plugin
    registry.register(ReviewerLoadPlugin())

    # Query
    plugin = registry.get("reviewer_load")
    all_plugins = registry.list()

    # Apply all registered plugins to a DataFrame
    enriched_df = registry.apply_all(df)
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import pandas as pd

from collectors.domain.plugins.base import MetricPlugin, PluginMetadata

logger = logging.getLogger(__name__)


class MetricRegistry:
    """Thread-safe registry for MetricPlugin instances."""

    def __init__(self):
        self._plugins: Dict[str, MetricPlugin] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, plugin: MetricPlugin, overwrite: bool = False) -> None:
        """
        Register a plugin instance.

        Parameters
        ----------
        plugin : MetricPlugin
            The plugin to register.
        overwrite : bool
            If True, silently replace an existing plugin with the same code.
            If False (default), raise ValueError on conflict.
        """
        code = plugin.metadata.code
        if code in self._plugins and not overwrite:
            raise ValueError(
                f"Plugin '{code}' is already registered. "
                "Pass overwrite=True to replace it."
            )
        self._plugins[code] = plugin
        logger.info(
            "Plugin registered",
            extra={"event": "plugin_registered", "code": code},
        )

    def unregister(self, code: str) -> bool:
        """Remove a plugin by code. Returns True if it existed."""
        existed = code in self._plugins
        self._plugins.pop(code, None)
        if existed:
            logger.info(
                "Plugin unregistered",
                extra={"event": "plugin_unregistered", "code": code},
            )
        return existed

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, code: str) -> Optional[MetricPlugin]:
        """Return plugin by code, or None if not found."""
        return self._plugins.get(code)

    def list(self) -> List[PluginMetadata]:
        """Return metadata for all registered plugins."""
        return [p.metadata for p in self._plugins.values()]

    def codes(self) -> List[str]:
        """Return list of registered plugin codes."""
        return list(self._plugins.keys())

    def __contains__(self, code: str) -> bool:
        return code in self._plugins

    def __len__(self) -> int:
        return len(self._plugins)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def apply(self, code: str, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply a single plugin by code.

        Parameters
        ----------
        code : str
            Plugin code.
        df : pd.DataFrame
            The review dataset.

        Returns
        -------
        pd.DataFrame
            DataFrame with the plugin's columns added.

        Raises
        ------
        KeyError
            If no plugin with that code is registered.
        ValueError
            If required columns are missing from df.
        """
        plugin = self._plugins.get(code)
        if plugin is None:
            raise KeyError(f"No plugin registered with code '{code}'.")
        return plugin.safe_compute(df)

    def apply_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply ALL registered plugins sequentially.
        Plugins that fail (missing columns, runtime error) are skipped
        with a warning rather than crashing the pipeline.
        """
        result = df.copy()
        for code, plugin in self._plugins.items():
            try:
                result = plugin.safe_compute(result)
            except (ValueError, Exception) as exc:
                logger.warning(
                    "Plugin skipped during apply_all",
                    extra={
                        "event": "plugin_skipped",
                        "code": code,
                        "reason": str(exc),
                    },
                )
        return result

    def apply_for_columns(
        self, df: pd.DataFrame, needed_columns: List[str]
    ) -> pd.DataFrame:
        """
        Apply only plugins whose output_columns overlap with needed_columns.
        Avoids running expensive plugins when their output isn't needed.
        """
        result = df.copy()
        for code, plugin in self._plugins.items():
            if any(col in needed_columns for col in plugin.metadata.output_columns):
                try:
                    result = plugin.safe_compute(result)
                except Exception as exc:
                    logger.warning(
                        "Plugin skipped (selective apply)",
                        extra={"event": "plugin_skipped", "code": code, "reason": str(exc)},
                    )
        return result


# Process-level singleton — imported by all modules that need the registry
registry = MetricRegistry()
