"""Dynamic strategy loader (``package.module:ClassName``).

The police brain class is a PRIVATE per-peer choice read from ``game.toml``
(``[strategy].police_class``), never negotiated. This loader resolves that
dotted path with a clear error if the module or class does not exist or is not
a :class:`PoliceBrainBase`.
"""

from __future__ import annotations

import importlib

from police_peer.strategy.base import PoliceBrainBase


class StrategyLoadError(Exception):
    """Raised when the configured strategy path cannot be resolved."""


def load_police_brain(dotted_path: str) -> PoliceBrainBase:
    """Instantiate the police brain named by ``module.path:ClassName``."""
    if ":" not in dotted_path:
        raise StrategyLoadError(f"strategy path must be 'module:ClassName', got {dotted_path!r}")
    module_name, class_name = dotted_path.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise StrategyLoadError(f"cannot import strategy module {module_name!r}: {exc}") from exc
    try:
        brain_class = getattr(module, class_name)
    except AttributeError as exc:
        raise StrategyLoadError(
            f"strategy class {class_name!r} not found in {module_name!r}"
        ) from exc
    if not (isinstance(brain_class, type) and issubclass(brain_class, PoliceBrainBase)):
        raise StrategyLoadError(f"{dotted_path!r} is not a PoliceBrainBase subclass")
    return brain_class()
