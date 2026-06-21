from PyQt5.QtWidgets import QGridLayout, QWidget

import config
from theme import Colors
from status_card import StatusCard


class ConnectionPanel(QWidget):
    """4 cards: status do link, qualidade do sinal, latência e controle Xbox."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setSpacing(10)

        self.card_link = StatusCard("Link ESP32", "Offline")
        self.card_quality = StatusCard("Qualidade do Sinal", "--")
        self.card_latency = StatusCard("Latência", "--")
        self.card_controller = StatusCard("Controle Xbox", "Desconectado")

        layout.addWidget(self.card_link, 0, 0)
        layout.addWidget(self.card_quality, 0, 1)
        layout.addWidget(self.card_latency, 1, 0)
        layout.addWidget(self.card_controller, 1, 1)

        self.card_link.set_state_color(Colors.GRAY)
        self.card_controller.set_state_color(Colors.GRAY)

    def update_link(self, quality):
        if quality.connected:
            self.card_link.set_value("Online", Colors.GREEN)
            self.card_link.set_state_color(Colors.GREEN)
            self.card_link.set_subtitle("Recebendo telemetria")
        else:
            self.card_link.set_value("Offline", Colors.RED)
            self.card_link.set_state_color(Colors.RED)
            self.card_link.set_subtitle("Sem pacotes recentes")

        q = quality.quality_percent
        color = Colors.GREEN if q >= 70 else Colors.YELLOW if q >= 30 else Colors.RED
        self.card_quality.set_value(f"{q}%", color if quality.connected else Colors.GRAY)
        self.card_quality.set_state_color(color if quality.connected else Colors.GRAY)
        self.card_quality.set_subtitle(f"{quality.packets_per_second} pacotes/s "
                                        f"(esperado: {config.EXPECTED_PACKET_RATE_HZ}/s)")

        if quality.latency_ms is not None:
            lat = quality.latency_ms
            color = (Colors.GREEN if lat < config.LATENCY_GOOD_MS else
                     Colors.YELLOW if lat < config.LATENCY_WARN_MS else Colors.RED)
            self.card_latency.set_value(f"{lat:.0f} ms", color)
            self.card_latency.set_state_color(color)
        else:
            self.card_latency.set_value("--")
            self.card_latency.set_state_color(Colors.GRAY)

    def update_controller(self, connected: bool):
        if connected:
            self.card_controller.set_value("Conectado", Colors.GREEN)
            self.card_controller.set_state_color(Colors.GREEN)
        else:
            self.card_controller.set_value("Desconectado", Colors.RED)
            self.card_controller.set_state_color(Colors.RED)