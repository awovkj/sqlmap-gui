from __future__ import annotations

import importlib
from typing import Iterable, List

from framework.plugins.base import Plugin


class PluginManager:
    def __init__(self, plugins: Iterable[Plugin] | None = None):
        self.plugins: List[Plugin] = list(plugins or [])

    @classmethod
    def load(cls, plugin_paths: Iterable[str]) -> "PluginManager":
        loaded = []
        for path in plugin_paths:
            module_name, _, attr = path.partition(":")
            module = importlib.import_module(module_name)
            plugin_cls = getattr(module, attr or "Plugin")
            loaded.append(plugin_cls())
        return cls(loaded)

    def emit(self, hook: str, *args, **kwargs) -> None:
        for plugin in self.plugins:
            callback = getattr(plugin, hook, None)
            if callable(callback):
                callback(*args, **kwargs)
