"""Numerical model and state classification for phase oscillators."""

from __future__ import annotations

from dataclasses import dataclass
from math import tau

import numpy as np
from numpy.typing import NDArray

from presets import get_preset

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class StateSummary:
    """Human-readable summary of the current oscillator configuration."""

    key: str
    label: str
    order_parameter: float
    pattern_clusters: int | None = None


class PhaseOscillatorSimulator:
    """Finite-dimensional all-to-all coupled phase oscillator model."""

    def __init__(
        self,
        count: int = 12,
        preset_key: str = "kuramoto_sync",
        coupling_strength: float = 1.5,
        frequency_spread: float = 0.0,
        seed: int = 7,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self.time = 0.0
        self.preset_key = preset_key
        self.coupling_strength = coupling_strength
        self.frequency_spread = frequency_spread
        self.phases = self._rng.uniform(0.0, tau, size=count)
        self.natural_frequencies = np.zeros(count, dtype=np.float64)
        self._refresh_natural_frequencies()

    @property
    def count(self) -> int:
        return int(self.phases.size)

    def set_count(self, count: int) -> None:
        if count < 1:
            raise ValueError("count must be positive")
        if count == self.count:
            return
        if count < self.count:
            self.phases = self.phases[:count].copy()
        else:
            added = self._rng.uniform(0.0, tau, size=count - self.count)
            self.phases = np.concatenate((self.phases, added))
        self._refresh_natural_frequencies()

    def set_preset(self, key: str) -> None:
        get_preset(key)
        self.preset_key = key

    def set_frequency_spread(self, spread: float) -> None:
        if spread < 0.0:
            raise ValueError("frequency spread must be non-negative")
        self.frequency_spread = spread
        self._refresh_natural_frequencies()

    def set_phase(self, index: int, angle: float) -> None:
        self.phases[index] = angle % tau

    def randomize(self) -> None:
        self.phases = self._rng.uniform(0.0, tau, size=self.count)
        self.time = 0.0

    def arrange_synchronized(self) -> None:
        self.phases.fill(0.0)
        self.time = 0.0

    def arrange_splay(self) -> None:
        self.phases = np.arange(self.count, dtype=np.float64) * tau / self.count
        self.time = 0.0

    def arrange_pattern(self, cluster_count: int) -> None:
        if self.count % cluster_count != 0:
            raise ValueError("cluster_count must be a divisor of count")
        self.phases = np.arange(self.count, dtype=np.float64) % cluster_count
        self.phases *= tau / cluster_count
        self.time = 0.0

    def order_parameter(self, harmonic: int = 1) -> float:
        if harmonic < 1:
            raise ValueError("harmonic must be positive")
        values = np.exp(1j * harmonic * self.phases)
        return float(np.abs(values.mean()))

    def velocity(self, phases: FloatArray | None = None) -> FloatArray:
        values = self.phases if phases is None else phases
        preset = get_preset(self.preset_key)
        if preset.phase_velocity is not None:
            return preset.phase_velocity(values)
        if preset.coupling is None:
            raise RuntimeError(f"preset has no coupling function: {preset.key}")
        delta = values[:, np.newaxis] - values[np.newaxis, :]
        interaction_matrix = preset.coupling(delta)
        np.fill_diagonal(interaction_matrix, 0.0)
        interaction = interaction_matrix.sum(axis=1)
        return self.natural_frequencies + self.coupling_strength * interaction / self.count

    def advance(self, seconds: float, max_step: float = 0.02) -> None:
        if seconds < 0.0:
            raise ValueError("seconds must be non-negative")
        if seconds == 0.0:
            return
        steps = max(1, int(np.ceil(seconds / max_step)))
        step = seconds / steps
        for _ in range(steps):
            theta = self.phases
            k1 = self.velocity(theta)
            k2 = self.velocity(theta + 0.5 * step * k1)
            k3 = self.velocity(theta + 0.5 * step * k2)
            k4 = self.velocity(theta + step * k3)
            self.phases = (theta + step * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0) % tau
        self.time += seconds

    def classify_state(self) -> StateSummary:
        r = self.order_parameter()
        if self.count == 1 or r >= 0.97:
            return StateSummary("sync", "phase synchronization", r, 1)

        for clusters in range(2, self.count + 1):
            if self.count % clusters:
                continue
            lower_orders = [self.order_parameter(h) for h in range(1, clusters)]
            if self.order_parameter(clusters) >= 0.95 and max(lower_orders) <= 0.15:
                if clusters == self.count:
                    return StateSummary("splay", "splay state", r, clusters)
                return StateSummary(
                    "pattern",
                    f"({clusters}, {self.count})-pattern",
                    r,
                    clusters,
                )

        if r <= 0.12:
            return StateSummary("balanced", "phase balancing", r)
        return StateSummary("transition", "transitioning / incoherent", r)

    def _refresh_natural_frequencies(self) -> None:
        if self.frequency_spread == 0.0:
            self.natural_frequencies = np.zeros(self.count, dtype=np.float64)
            return
        frequencies = self._rng.uniform(
            -self.frequency_spread,
            self.frequency_spread,
            size=self.count,
        )
        self.natural_frequencies = frequencies - frequencies.mean()
