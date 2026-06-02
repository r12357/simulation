"""Coupling-function presets for the phase oscillator simulator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
CouplingFunction = Callable[[FloatArray], FloatArray]


@dataclass(frozen=True)
class CouplingPreset:
    """A selectable coupling function and its display metadata."""

    key: str
    label: str
    description: str
    coupling: CouplingFunction
    suggested_clusters: int | None = None


_PRESETS: dict[str, CouplingPreset] = {}


def register_preset(preset: CouplingPreset) -> None:
    """Register a preset so that the GUI can include it in the pull-down."""

    if not preset.key:
        raise ValueError("preset.key must not be empty")
    if preset.key in _PRESETS:
        raise ValueError(f"preset key is already registered: {preset.key}")
    _PRESETS[preset.key] = preset


def list_presets() -> tuple[CouplingPreset, ...]:
    """Return registered presets in GUI display order."""

    return tuple(_PRESETS.values())


def get_preset(key: str) -> CouplingPreset:
    """Return the registered preset identified by key."""

    try:
        return _PRESETS[key]
    except KeyError as exc:
        raise KeyError(f"unknown preset: {key}") from exc


def pattern_coupling(cluster_count: int) -> CouplingFunction:
    """Build the higher-harmonic coupling used for an (m, n)-pattern."""

    if cluster_count < 2:
        raise ValueError("cluster_count must be at least 2")

    def coupling(delta: FloatArray) -> FloatArray:
        result = np.zeros_like(delta)
        for harmonic in range(1, cluster_count + 1):
            gain = -1.0 if harmonic == cluster_count else 1.0
            result += (gain / harmonic) * np.sin(harmonic * delta)
        return result

    return coupling


def _register_defaults() -> None:
    register_preset(
        CouplingPreset(
            key="kuramoto_sync",
            label="Kuramoto: sync",
            description="Attractive sinusoidal coupling. Phases approach synchronization.",
            coupling=lambda delta: -np.sin(delta),
            suggested_clusters=1,
        )
    )
    register_preset(
        CouplingPreset(
            key="phase_balance",
            label="Repulsive: phase balancing",
            description="Repulsive sinusoidal coupling from equation (34).",
            coupling=lambda delta: np.sin(delta),
        )
    )
    for cluster_count in (2, 3, 4, 5, 6):
        register_preset(
            CouplingPreset(
                key=f"pattern_m{cluster_count}",
                label=f"Harmonics: ({cluster_count}, n)-pattern",
                description=(
                    "Higher-harmonic pattern-forming coupling from equation (35), "
                    f"with m={cluster_count}."
                ),
                coupling=pattern_coupling(cluster_count),
                suggested_clusters=cluster_count,
            )
        )


_register_defaults()
