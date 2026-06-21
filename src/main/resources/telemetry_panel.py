from PyQt5.QtWidgets import QGridLayout, QWidget

from theme import Colors
from status_card import StatusCard


class TelemetryPanel(QWidget):
    """Mostra a IMU recebida (roll/pitch/yaw) e os comandos enviados
    ao transmissor (throttle/aileron/rudder/elevator), lado a lado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setSpacing(10)

        self.card_roll = StatusCard("Roll", "0.0°")
        self.card_pitch = StatusCard("Pitch", "0.0°")
        self.card_yaw = StatusCard("Yaw", "0.0°")
        for i, c in enumerate((self.card_roll, self.card_pitch, self.card_yaw)):
            layout.addWidget(c, 0, i)

        self.card_throttle = StatusCard("Throttle", "1000 µs")
        self.card_aileron = StatusCard("Aileron", "1500 µs")
        self.card_rudder = StatusCard("Rudder", "1500 µs")
        self.card_elevator = StatusCard("Elevator", "1500 µs")
        for i, c in enumerate(
            [self.card_throttle, self.card_aileron, self.card_rudder, self.card_elevator]
        ):
            layout.addWidget(c, 1, i)

    def update_imu(self, imu):
        self.card_roll.set_value(f"{imu.roll:.1f}°", Colors.ACCENT)
        self.card_pitch.set_value(f"{imu.pitch:.1f}°", Colors.ACCENT)
        self.card_yaw.set_value(f"{imu.yaw:.1f}°", Colors.ACCENT)

    def update_command(self, cmd):
        self.card_throttle.set_value(f"{cmd.throttle} µs")
        self.card_aileron.set_value(f"{cmd.aileron} µs")
        self.card_rudder.set_value(f"{cmd.rudder} µs")
        self.card_elevator.set_value(f"{cmd.elevator} µs")