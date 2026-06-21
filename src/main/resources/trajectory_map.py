"""
Mapa de trajetória offline (matplotlib) — não depende de internet nem de
QtWebEngine, então funciona mesmo quando o PC está conectado apenas à
rede WiFi do próprio ESP32 (sem acesso à internet para baixar tiles).

Possível evolução futura: trocar por QWebEngineView + Leaflet/OpenStreetMap
para tiles reais, mantendo a mesma interface pública (add_gps_point) — ver
README.md, seção "Próximos passos".
"""
import webbrowser

import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout, QWidget

from models import GpsFixState
from theme import Colors


class TrajectoryMap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.trajectory = []  # lista de (lon, lat)

        layout = QVBoxLayout(self)

        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.fig.patch.set_facecolor(Colors.SURFACE)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas, 1)
        self._style_axes()

        btn_row = QHBoxLayout()
        self.btn_maps = QPushButton("Abrir no Google Maps")
        self.btn_save = QPushButton("Salvar Imagem")
        self.btn_clear = QPushButton("Limpar Trajetória")
        self.btn_maps.clicked.connect(self._abrir_maps)
        self.btn_save.clicked.connect(self._salvar)
        self.btn_clear.clicked.connect(self._limpar)
        btn_row.addWidget(self.btn_maps)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_clear)
        layout.addLayout(btn_row)

    def _style_axes(self):
        self.ax.clear()
        self.ax.set_facecolor(Colors.SURFACE)
        self.ax.set_title("Trajetória do Aeromodelo", color=Colors.TEXT)
        self.ax.set_xlabel("Longitude", color=Colors.TEXT_MUTED)
        self.ax.set_ylabel("Latitude", color=Colors.TEXT_MUTED)
        self.ax.tick_params(colors=Colors.TEXT_MUTED, labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color(Colors.BORDER)
        self.ax.grid(True, color=Colors.BORDER, linewidth=0.5)

    def add_gps_point(self, gps):
        if gps.fix != GpsFixState.FIX_VALIDO:
            return
        point = (gps.lon, gps.lat)
        if not self.trajectory or point != self.trajectory[-1]:
            self.trajectory.append(point)
        self._redraw(current=point)

    def _redraw(self, current=None):
        self._style_axes()
        if self.trajectory:
            lons, lats = zip(*self.trajectory)
            self.ax.plot(lons, lats, "-", color=Colors.ACCENT, linewidth=1.5, alpha=0.85)
        if current:
            self.ax.plot(current[0], current[1], "o", color=Colors.GREEN,
                          markersize=10, markeredgecolor="white", markeredgewidth=1.2,
                          zorder=5)
        self.canvas.draw_idle()

    def _abrir_maps(self):
        if self.trajectory:
            lon, lat = self.trajectory[-1]
            webbrowser.open(f"https://www.google.com/maps?q={lat},{lon}")
        else:
            QMessageBox.information(self, "Sem dados", "Nenhuma posição de GPS válida recebida ainda.")

    def _salvar(self):
        self.fig.savefig("trajetoria.png", facecolor=self.fig.get_facecolor())
        QMessageBox.information(self, "Salvo", "Imagem salva como trajetoria.png")

    def _limpar(self):
        self.trajectory.clear()
        self._redraw()