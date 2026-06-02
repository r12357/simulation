"""Unit tests for the GUI-independent oscillator model."""

from __future__ import annotations

import unittest

import numpy as np

from presets import CouplingPreset, cotangent_neighbor_velocity, get_preset, register_preset
from simulator import PhaseOscillatorSimulator


class PhaseOscillatorSimulatorTests(unittest.TestCase):
    def test_synchronized_configuration_is_classified(self) -> None:
        simulator = PhaseOscillatorSimulator(count=8)
        simulator.arrange_synchronized()

        summary = simulator.classify_state()

        self.assertEqual(summary.key, "sync")
        self.assertAlmostEqual(summary.order_parameter, 1.0)

    def test_splay_configuration_is_classified(self) -> None:
        simulator = PhaseOscillatorSimulator(count=8)
        simulator.arrange_splay()

        summary = simulator.classify_state()

        self.assertEqual(summary.key, "splay")
        self.assertEqual(summary.pattern_clusters, 8)

    def test_symmetric_cluster_pattern_is_classified(self) -> None:
        simulator = PhaseOscillatorSimulator(count=12)
        simulator.arrange_pattern(3)

        summary = simulator.classify_state()

        self.assertEqual(summary.key, "pattern")
        self.assertEqual(summary.pattern_clusters, 3)
        self.assertEqual(summary.label, "(3, 12)-pattern")

    def test_attractive_kuramoto_coupling_increases_coherence(self) -> None:
        simulator = PhaseOscillatorSimulator(count=5, coupling_strength=2.0)
        simulator.phases = np.array([0.0, 0.9, 1.8, 3.1, 4.6])
        before = simulator.order_parameter()

        simulator.advance(4.0)

        self.assertGreater(simulator.order_parameter(), before)
        self.assertEqual(simulator.classify_state().key, "sync")

    def test_repulsive_coupling_reaches_phase_balancing(self) -> None:
        simulator = PhaseOscillatorSimulator(
            count=12,
            preset_key="phase_balance",
            coupling_strength=2.0,
        )

        simulator.advance(12.0)

        self.assertLess(simulator.order_parameter(), 0.01)
        self.assertEqual(simulator.classify_state().key, "balanced")

    def test_pattern_coupling_recovers_cluster_pattern_after_perturbation(self) -> None:
        simulator = PhaseOscillatorSimulator(
            count=12,
            preset_key="pattern_m3",
            coupling_strength=2.0,
        )
        simulator.arrange_pattern(3)
        simulator.phases += np.linspace(-0.12, 0.12, simulator.count)

        simulator.advance(8.0)

        self.assertGreater(simulator.order_parameter(3), 0.99)
        self.assertEqual(simulator.classify_state().label, "(3, 12)-pattern")

    def test_registered_custom_preset_can_be_selected(self) -> None:
        register_preset(
            CouplingPreset(
                key="test_zero_coupling",
                label="Test: zero coupling",
                description="Used only by the unit test.",
                coupling=lambda delta: np.zeros_like(delta),
            )
        )
        simulator = PhaseOscillatorSimulator(count=3)
        simulator.set_preset("test_zero_coupling")
        initial = simulator.phases.copy()

        simulator.advance(1.0)

        np.testing.assert_allclose(simulator.phases, initial)

    def test_pattern_requires_divisor_of_count(self) -> None:
        simulator = PhaseOscillatorSimulator(count=10)

        with self.assertRaises(ValueError):
            simulator.arrange_pattern(3)

    def test_additional_presets_are_registered(self) -> None:
        keys = (
            "two_harmonic_sync",
            "two_cluster_sync",
            "three_cluster_sync",
            "sakaguchi_lag",
            "mixed_attractive_repulsive",
            "cotangent_neighbor_flow",
        )

        for key in keys:
            with self.subTest(key=key):
                self.assertEqual(get_preset(key).key, key)

    def test_cotangent_neighbor_flow_uses_cyclic_boundary(self) -> None:
        simulator = PhaseOscillatorSimulator(
            count=4,
            preset_key="cotangent_neighbor_flow",
            coupling_strength=99.0,
            frequency_spread=5.0,
        )
        simulator.phases = np.array([0.2, 1.4, 3.1, 5.2])
        previous_gap = simulator.phases - np.roll(simulator.phases, 1)
        next_gap = np.roll(simulator.phases, -1) - simulator.phases
        expected = 0.5 * (
            1.0 / np.tan(previous_gap / 2.0)
            - 1.0 / np.tan(next_gap / 2.0)
        )

        np.testing.assert_allclose(simulator.velocity(), expected)

    def test_cotangent_neighbor_flow_has_splay_equilibrium(self) -> None:
        simulator = PhaseOscillatorSimulator(
            count=12,
            preset_key="cotangent_neighbor_flow",
        )
        simulator.arrange_splay()

        np.testing.assert_allclose(simulator.velocity(), np.zeros(12), atol=1e-12)

    def test_cotangent_neighbor_flow_regularizes_collision(self) -> None:
        values = np.array([0.0, 0.0, 1.0, 3.0])

        self.assertTrue(np.isfinite(cotangent_neighbor_velocity(values)).all())


if __name__ == "__main__":
    unittest.main()
