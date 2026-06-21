from PyQt5.QtWidgets import QGridLayout, QWidget

import config
from models import GpsFixState
from theme import Colors
from status_card import StatusCard


class GpsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setSpacing(10)

        self.card_fix = StatusCard("Status do GPS", "Sem dados")
        self.card_lat = StatusCard("Latitude", "--")
        self.card_lon = StatusCard("Longitude", "--")
        self.card_alt = StatusCard("Altitude", "-- m")
        self.card_spd = StatusCard("Velocidade", "-- km/h")
        self.card_sats = StatusCard("Satélites", "--")
        self.card_time = StatusCard("Data/Hora UTC", "--")

        cards = [self.card_fix, self.card_lat, self.card_lon,
                 self.card_alt, self.card_spd, self.card_sats, self.card_time]
        for i, c in enumerate(cards):
            layout.addWidget(c, i // 4, i % 4)

        self.card_fix.set_state_color(Colors.GRAY)
        self.card_sats.set_state_color(Colors.GRAY)

    def update_gps(self, gps):
        if gps.fix == GpsFixState.FIX_VALIDO:
            self.card_fix.set_value("Fix válido", Colors.GREEN)
            self.card_fix.set_state_color(Colors.GREEN)
            self.card_lat.set_value(f"{gps.lat:.6f}")
            self.card_lon.set_value(f"{gps.lon:.6f}")
            self.card_alt.set_value(f"{gps.altitude:.1f} m")
            self.card_spd.set_value(f"{gps.speed_kmh:.1f} km/h")
        else:
            self.card_fix.set_value("Sem fix", Colors.RED)
            self.card_fix.set_state_color(Colors.RED)
            self.card_lat.set_value("--")
            self.card_lon.set_value("--")
            self.card_alt.set_value("-- m")
            self.card_spd.set_value("-- km/h")

        self.card_sats.set_value(str(gps.satellites))
        sat_color = (
            Colors.GREEN if gps.satellites >= config.GPS_MIN_SATS_GOOD else
            Colors.YELLOW if gps.satellites >= config.GPS_MIN_SATS_OK else
            Colors.RED
        )
        self.card_sats.set_state_color(sat_color)
        self.card_time.set_value(f"{gps.date_str}  {gps.time_str}")