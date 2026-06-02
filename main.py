"""PySide6 desktop GUI for exploring coupled phase oscillators."""

from __future__ import annotations

import math
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from presets import get_preset, list_presets
from simulator import PhaseOscillatorSimulator


class OscillatorCanvas(QtWidgets.QWidget):
    """Interactive circle view for selecting and dragging oscillator phases."""

    phase_changed = QtCore.Signal(int, float)
    selected_changed = QtCore.Signal(int)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._phases: tuple[float, ...] = ()
        self._selected = 0
        self.setMinimumSize(560, 560)
        self.setMouseTracking(True)

    def set_phases(self, phases: object) -> None:
        self._phases = tuple(float(value) for value in phases)
        if self._phases:
            self._selected = min(self._selected, len(self._phases) - 1)
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor("#0f172a"))

        center, radius = self._circle()
        painter.setPen(QtGui.QPen(QtGui.QColor("#334155"), 2))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

        for tick in range(12):
            angle = tick * math.tau / 12
            outer = self._point(center, radius + 5, angle)
            inner = self._point(center, radius - 5, angle)
            painter.setPen(QtGui.QPen(QtGui.QColor("#475569"), 2))
            painter.drawLine(inner, outer)

        if not self._phases:
            return

        mean_x = sum(math.cos(value) for value in self._phases) / len(self._phases)
        mean_y = sum(math.sin(value) for value in self._phases) / len(self._phases)
        centroid = QtCore.QPointF(
            center.x() + radius * mean_x,
            center.y() - radius * mean_y,
        )
        painter.setPen(
            QtGui.QPen(
                QtGui.QColor("#38bdf8"),
                3,
                QtCore.Qt.PenStyle.DashLine,
            )
        )
        painter.drawLine(center, centroid)
        painter.setBrush(QtGui.QColor("#38bdf8"))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(centroid, 6, 6)

        for index, angle in enumerate(self._phases):
            point = self._point(center, radius, angle)
            if index == self._selected:
                painter.setBrush(QtGui.QColor("#f8fafc"))
                painter.setPen(QtGui.QPen(QtGui.QColor("#38bdf8"), 4))
                dot_radius = 13
            else:
                painter.setBrush(QtGui.QColor("#f59e0b"))
                painter.setPen(QtGui.QPen(QtGui.QColor("#fef3c7"), 2))
                dot_radius = 10
            painter.drawEllipse(point, dot_radius, dot_radius)
            painter.setPen(QtGui.QColor("#0f172a"))
            painter.drawText(
                QtCore.QRectF(point.x() - 13, point.y() - 10, 26, 20),
                QtCore.Qt.AlignmentFlag.AlignCenter,
                str(index + 1),
            )

        painter.setPen(QtGui.QColor("#94a3b8"))
        painter.drawText(
            QtCore.QRectF(16, self.height() - 42, self.width() - 32, 26),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            "Drag a transmitter around the circle to set its phase.",
        )

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() != QtCore.Qt.MouseButton.LeftButton or not self._phases:
            return
        center, radius = self._circle()
        points = [self._point(center, radius, angle) for angle in self._phases]
        distances = [
            math.hypot(event.position().x() - point.x(), event.position().y() - point.y())
            for point in points
        ]
        if min(distances) <= 24:
            self._selected = distances.index(min(distances))
            self.selected_changed.emit(self._selected)
        else:
            self._emit_position(event.position())
        self.update()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self._emit_position(event.position())

    def _emit_position(self, point: QtCore.QPointF) -> None:
        center, _ = self._circle()
        angle = math.atan2(center.y() - point.y(), point.x() - center.x()) % math.tau
        self.phase_changed.emit(self._selected, angle)

    def _circle(self) -> tuple[QtCore.QPointF, float]:
        center = QtCore.QPointF(self.width() / 2, self.height() / 2 - 8)
        radius = max(40.0, min(self.width(), self.height()) * 0.36)
        return center, radius

    @staticmethod
    def _point(center: QtCore.QPointF, radius: float, angle: float) -> QtCore.QPointF:
        return QtCore.QPointF(
            center.x() + radius * math.cos(angle),
            center.y() - radius * math.sin(angle),
        )


class MainWindow(QtWidgets.QMainWindow):
    """Main application window and timer coordination."""

    def __init__(self) -> None:
        super().__init__()
        self.simulator = PhaseOscillatorSimulator()
        self.running = False
        self.speed = 1.0
        self.selected_index = 0

        self.setWindowTitle("Phase Oscillator Studio")
        self.resize(1180, 760)
        self.setMinimumSize(980, 680)
        self._build_ui()
        self._connect_signals()
        self._refresh()

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    def _build_ui(self) -> None:
        root = QtWidgets.QWidget()
        root.setObjectName("root")
        layout = QtWidgets.QHBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)
        self.setCentralWidget(root)

        left = self._card()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(18, 16, 18, 16)
        title = QtWidgets.QLabel("Phase Oscillator Studio")
        title.setObjectName("title")
        subtitle = QtWidgets.QLabel("Kuramoto model, balancing, and harmonic patterns")
        subtitle.setObjectName("subtitle")
        self.canvas = OscillatorCanvas()
        left_layout.addWidget(title)
        left_layout.addWidget(subtitle)
        left_layout.addWidget(self.canvas, 1)
        layout.addWidget(left, 1)

        panel = QtWidgets.QScrollArea()
        panel.setWidgetResizable(True)
        panel.setFixedWidth(360)
        panel.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        panel_content = QtWidgets.QWidget()
        panel_layout = QtWidgets.QVBoxLayout(panel_content)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(12)
        panel.setWidget(panel_content)
        layout.addWidget(panel)

        status_card = self._card()
        status_layout = QtWidgets.QVBoxLayout(status_card)
        status_layout.addWidget(self._section_title("状態"))
        self.state_value = QtWidgets.QLabel()
        self.state_value.setObjectName("stateBadge")
        self.state_value.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.state_value)
        grid = QtWidgets.QGridLayout()
        self.count_value = QtWidgets.QLabel()
        self.time_value = QtWidgets.QLabel()
        self.order_value = QtWidgets.QLabel()
        self.selected_value = QtWidgets.QLabel()
        self._grid_metric(grid, 0, "発信機数", self.count_value)
        self._grid_metric(grid, 1, "時刻", self.time_value)
        self._grid_metric(grid, 2, "order parameter", self.order_value)
        self._grid_metric(grid, 3, "選択中", self.selected_value)
        status_layout.addLayout(grid)
        panel_layout.addWidget(status_card)

        simulation_card = self._card()
        simulation_layout = QtWidgets.QVBoxLayout(simulation_card)
        simulation_layout.addWidget(self._section_title("Simulation"))
        transport = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("開始")
        self.step_button = QtWidgets.QPushButton("1 step")
        transport.addWidget(self.start_button)
        transport.addWidget(self.step_button)
        simulation_layout.addLayout(transport)
        self.random_button = QtWidgets.QPushButton("ランダム配置へ戻す")
        simulation_layout.addWidget(self.random_button)
        panel_layout.addWidget(simulation_card)

        settings_card = self._card()
        settings_layout = QtWidgets.QFormLayout(settings_card)
        settings_layout.setContentsMargins(14, 14, 14, 14)
        settings_layout.setVerticalSpacing(12)
        settings_layout.addRow(self._section_title("設定"))
        self.count_spin = QtWidgets.QSpinBox()
        self.count_spin.setRange(1, 64)
        self.count_spin.setValue(self.simulator.count)
        settings_layout.addRow("発信機数", self.count_spin)
        self.coupling_spin = QtWidgets.QDoubleSpinBox()
        self.coupling_spin.setRange(0.0, 20.0)
        self.coupling_spin.setDecimals(2)
        self.coupling_spin.setSingleStep(0.1)
        self.coupling_spin.setValue(self.simulator.coupling_strength)
        settings_layout.addRow("結合強度 K", self.coupling_spin)
        self.spread_spin = QtWidgets.QDoubleSpinBox()
        self.spread_spin.setRange(0.0, 5.0)
        self.spread_spin.setDecimals(2)
        self.spread_spin.setSingleStep(0.05)
        self.spread_spin.setValue(self.simulator.frequency_spread)
        settings_layout.addRow("周波数ばらつき", self.spread_spin)
        speed_row = QtWidgets.QWidget()
        speed_layout = QtWidgets.QHBoxLayout(speed_row)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        self.speed_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 100)
        self.speed_slider.setValue(50)
        self.speed_label = QtWidgets.QLabel("1.00x")
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)
        settings_layout.addRow("進行速度", speed_row)
        panel_layout.addWidget(settings_card)

        preset_card = self._card()
        preset_layout = QtWidgets.QVBoxLayout(preset_card)
        preset_layout.addWidget(self._section_title("関数プリセット"))
        self.preset_combo = QtWidgets.QComboBox()
        for preset in list_presets():
            self.preset_combo.addItem(preset.label, preset.key)
        preset_layout.addWidget(self.preset_combo)
        self.preset_description = QtWidgets.QLabel()
        self.preset_description.setWordWrap(True)
        self.preset_description.setObjectName("description")
        preset_layout.addWidget(self.preset_description)
        self.example_button = QtWidgets.QPushButton("プリセット例を配置")
        preset_layout.addWidget(self.example_button)
        panel_layout.addWidget(preset_card)
        panel_layout.addStretch()

        self.setStyleSheet(
            """
            QWidget#root { background: #020617; color: #e2e8f0; }
            QFrame#card { background: #0f172a; border: 1px solid #1e293b;
                          border-radius: 14px; }
            QLabel#title { color: #f8fafc; font-size: 24px; font-weight: 700; }
            QLabel#subtitle, QLabel#description { color: #94a3b8; }
            QLabel#sectionTitle { color: #38bdf8; font-size: 13px;
                                  font-weight: 700; }
            QLabel#stateBadge { background: #164e63; color: #cffafe;
                                border-radius: 8px; padding: 9px; font-weight: 700; }
            QPushButton { background: #1e293b; color: #f8fafc; border: 1px solid #334155;
                          border-radius: 7px; padding: 8px; }
            QPushButton:hover { background: #334155; }
            QPushButton:pressed { background: #0c4a6e; }
            QSpinBox, QDoubleSpinBox, QComboBox { background: #020617; color: #f8fafc;
                                                 border: 1px solid #334155;
                                                 border-radius: 5px; padding: 5px; }
            QScrollArea { background: transparent; }
            """
        )

    def _connect_signals(self) -> None:
        self.start_button.clicked.connect(self._toggle_running)
        self.step_button.clicked.connect(lambda: self._advance(0.03))
        self.random_button.clicked.connect(self._randomize)
        self.example_button.clicked.connect(self._arrange_example)
        self.count_spin.valueChanged.connect(self._change_count)
        self.coupling_spin.valueChanged.connect(self._change_coupling)
        self.spread_spin.valueChanged.connect(self._change_spread)
        self.speed_slider.valueChanged.connect(self._change_speed)
        self.preset_combo.currentIndexChanged.connect(self._change_preset)
        self.canvas.phase_changed.connect(self._move_phase)
        self.canvas.selected_changed.connect(self._select_oscillator)

    def _on_tick(self) -> None:
        if self.running:
            self._advance(0.033 * self.speed)

    def _advance(self, seconds: float) -> None:
        self.simulator.advance(seconds)
        self._refresh()

    def _toggle_running(self) -> None:
        self.running = not self.running
        self.start_button.setText("一時停止" if self.running else "開始")

    def _randomize(self) -> None:
        self.simulator.randomize()
        self._refresh()

    def _arrange_example(self) -> None:
        preset = get_preset(self.simulator.preset_key)
        if preset.suggested_clusters == 1:
            self.simulator.arrange_synchronized()
        elif preset.suggested_clusters is None:
            self.simulator.arrange_splay()
        elif self.simulator.count % preset.suggested_clusters == 0:
            self.simulator.arrange_pattern(preset.suggested_clusters)
        else:
            QtWidgets.QMessageBox.information(
                self,
                "配置できません",
                "発信機数を m の倍数にすると、このプリセット例を配置できます。",
            )
            return
        self._refresh()

    def _change_count(self, count: int) -> None:
        self.simulator.set_count(count)
        self.selected_index = min(self.selected_index, count - 1)
        self._refresh()

    def _change_coupling(self, value: float) -> None:
        self.simulator.coupling_strength = value

    def _change_spread(self, value: float) -> None:
        self.simulator.set_frequency_spread(value)
        self._refresh()

    def _change_speed(self, value: int) -> None:
        self.speed = 2.0 ** ((value - 50) / 25)
        self.speed_label.setText(f"{self.speed:.2f}x")

    def _change_preset(self) -> None:
        self.simulator.set_preset(self.preset_combo.currentData())
        self._refresh()

    def _move_phase(self, index: int, angle: float) -> None:
        self.simulator.set_phase(index, angle)
        self._refresh()

    def _select_oscillator(self, index: int) -> None:
        self.selected_index = index
        self._refresh()

    def _refresh(self) -> None:
        summary = self.simulator.classify_state()
        self.canvas.set_phases(self.simulator.phases)
        self.count_value.setText(str(self.simulator.count))
        self.time_value.setText(f"{self.simulator.time:.2f}")
        self.order_value.setText(f"{summary.order_parameter:.3f}")
        self.selected_value.setText(f"#{self.selected_index + 1}")
        self.state_value.setText(summary.label)
        self.state_value.setStyleSheet(self._status_style(summary.key))
        preset = get_preset(self.simulator.preset_key)
        self.preset_description.setText(preset.description)
        uses_standard_parameters = preset.phase_velocity is None
        self.coupling_spin.setEnabled(uses_standard_parameters)
        self.spread_spin.setEnabled(uses_standard_parameters)

    @staticmethod
    def _status_style(key: str) -> str:
        colors = {
            "sync": ("#14532d", "#dcfce7"),
            "splay": ("#581c87", "#f3e8ff"),
            "pattern": ("#312e81", "#e0e7ff"),
            "balanced": ("#164e63", "#cffafe"),
            "transition": ("#78350f", "#fef3c7"),
        }
        background, foreground = colors[key]
        return (
            f"background: {background}; color: {foreground}; "
            "border-radius: 8px; padding: 9px; font-weight: 700;"
        )

    @staticmethod
    def _card() -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("card")
        return card

    @staticmethod
    def _section_title(text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    @staticmethod
    def _grid_metric(grid: QtWidgets.QGridLayout, row: int, title: str, value: QtWidgets.QLabel) -> None:
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("description")
        grid.addWidget(title_label, row, 0)
        grid.addWidget(value, row, 1, alignment=QtCore.Qt.AlignmentFlag.AlignRight)


def run() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Phase Oscillator Studio")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
