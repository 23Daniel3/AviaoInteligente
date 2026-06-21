from PyQt5.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from models import PowerState
from theme import Colors
from status_card import StatusCard

_STATE_LABELS = {
    PowerState.NORMAL: ("Normal", Colors.GREEN),
    PowerState.BAIXA: ("Baixa", Colors.YELLOW),
    PowerState.CRITICA: ("Crítica", Colors.RED),
    PowerState.DESCONHECIDO: ("Sem dados", Colors.GRAY),
}


class BatteryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setSpacing(10)

        self.card_voltage = StatusCard("Tensão da Bateria", "-- V")
        self.card_state = StatusCard("Estado de Energia", "Sem dados")
        layout.addWidget(self.card_voltage)
        layout.addWidget(self.card_state)

        bar_card = QWidget()
        bar_layout = QVBoxLayout(bar_card)
        bar_layout.setContentsMargins(14, 10, 14, 12)
        label = QLabel("CARGA ESTIMADA")
        label.setObjectName("cardTitle")
        bar_layout.addWidget(label)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFormat("%p%")
        bar_layout.addWidget(self.bar)
        bar_layout.addStretch()
        bar_card.setStyleSheet(f"background: {Colors.SURFACE}; border: 1px solid {Colors.BORDER}; "
                                f"border-radius: 10px;")
        layout.addWidget(bar_card)

        self.card_state.set_state_color(Colors.GRAY)

    def update_battery(self, battery):
        self.card_voltage.set_value(f"{battery.voltage:.2f} V")
        label, color = _STATE_LABELS[battery.state]
        self.card_state.set_value(label, color)
        self.card_state.set_state_color(color)
        self.card_voltage.set_state_color(color)

        self.bar.setValue(int(round(battery.percent)))
        self.bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")