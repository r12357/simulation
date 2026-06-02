"""Coupling-function presets for the phase oscillator simulator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
CouplingFunction = Callable[[FloatArray], FloatArray]
PhaseVelocityFunction = Callable[[FloatArray], FloatArray]


@dataclass(frozen=True)
class CouplingPreset:
    """A selectable coupling function and its display metadata."""

    key: str
    label: str
    description: str
    coupling: CouplingFunction | None = None
    phase_velocity: PhaseVelocityFunction | None = None
    suggested_clusters: int | None = None


_PRESETS: dict[str, CouplingPreset] = {}


def register_preset(preset: CouplingPreset) -> None:
    """Register a preset so that the GUI can include it in the pull-down."""

    if not preset.key:
        raise ValueError("preset.key must not be empty")
    if preset.key in _PRESETS:
        raise ValueError(f"preset key is already registered: {preset.key}")
    if (preset.coupling is None) == (preset.phase_velocity is None):
        raise ValueError("preset must define exactly one velocity function")
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


def cotangent_neighbor_velocity(phases: FloatArray) -> FloatArray:
    """Return the cyclic nearest-neighbor cotangent velocity field."""

    if phases.size == 1:
        return np.zeros_like(phases)
    previous_gap = phases - np.roll(phases, 1)
    next_gap = np.roll(phases, -1) - phases
    return 0.5 * (_safe_cot(previous_gap / 2.0) - _safe_cot(next_gap / 2.0))


def _safe_cot(values: FloatArray, epsilon: float = 1e-8) -> FloatArray:
    """Evaluate cotangent while keeping collision singularities finite."""

    sine = np.sin(values)
    signs = np.where(sine >= 0.0, 1.0, -1.0)
    denominator = np.where(np.abs(sine) < epsilon, signs * epsilon, sine)
    return np.cos(values) / denominator


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
    register_preset(
        CouplingPreset(
            key="two_harmonic_sync",
            label="Mixed harmonics: sync",
            description="Attractive first and second harmonics for sharper synchronization.",
            coupling=lambda delta: -np.sin(delta) - 0.3 * np.sin(2.0 * delta),
            suggested_clusters=1,
        )
    )
    register_preset(
        CouplingPreset(
            key="two_cluster_sync",
            label="Pure harmonic: 2 clusters",
            description="Attractive second harmonic. Two phase clusters can emerge.",
            coupling=lambda delta: -np.sin(2.0 * delta),
            suggested_clusters=2,
        )
    )
    register_preset(
        CouplingPreset(
            key="three_cluster_sync",
            label="Pure harmonic: 3 clusters",
            description="Attractive third harmonic. Three phase clusters can emerge.",
            coupling=lambda delta: -np.sin(3.0 * delta),
            suggested_clusters=3,
        )
    )
    register_preset(
        CouplingPreset(
            key="sakaguchi_lag",
            label="Sakaguchi-Kuramoto: phase lag",
            description="Attractive sinusoidal coupling with a phase lag of pi / 4.",
            coupling=lambda delta: -np.sin(delta + np.pi / 4.0),
        )
    )
    register_preset(
        CouplingPreset(
            key="mixed_attractive_repulsive",
            label="Mixed: attractive / repulsive",
            description="Competing attractive first and repulsive second harmonics.",
            coupling=lambda delta: -np.sin(delta) + 0.7 * np.sin(2.0 * delta),
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
    register_preset(
        CouplingPreset(
            key="cotangent_neighbor_flow",
            label="Cyclic neighbors: cotangent flow",
            description=(
                "Cyclic nearest-neighbor cotangent flow. This exact preset uses neither "
                "coupling strength K nor natural-frequency spread."
            ),
            phase_velocity=cotangent_neighbor_velocity,
        )
    )


_register_defaults()
