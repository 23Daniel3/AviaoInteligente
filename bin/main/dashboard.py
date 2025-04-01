import os
import sys
import numpy as np
import pyvista as pv
from scipy.spatial.transform import Rotation as R
import webbrowser
import matplotlib
import time
from PyQt5.QtCore import QTimer
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QDoubleSpinBox, QLineEdit, QPushButton, QMessageBox, QSizePolicy
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from pyvistaqt import QtInteractor
from resources.util import XboxController

# Caminho do modelo CAD
modelo_path = "C:/Users/danie/Desktop/Programacao/Avião Inteligente/src/main/resources/modelo.obj"
if not os.path.exists(modelo_path):
    print(f"Erro: Arquivo {modelo_path} não encontrado!")
    sys.exit(1)

# Carregar modelo CAD
modelo_original = pv.read(modelo_path)
modelo = modelo_original.copy()
centroide = modelo.points.mean(axis=0)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard de Monitoramento")
        self.resize(1600, 900)

        self.trajectory = []
        self.animating = False
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_rotation)
        self.animation_step = 0

        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # Painel esquerdo
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        main_layout.addWidget(left_panel, 3)

        # Visualizador 3D
        self.plotter = QtInteractor(self)
        self.plotter.add_mesh(modelo, color="white")
        self.plotter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.plotter, 5)

        # Controles de rotação
        rot_group = QWidget()
        rot_layout = QGridLayout(rot_group)
        left_layout.addWidget(rot_group, 1)

        lbl_yaw = QLabel("Yaw:")
        self.spin_yaw = QDoubleSpinBox()
        self.spin_yaw.setRange(-180, 180)
        self.spin_yaw.setDecimals(2)
        self.spin_yaw.setValue(0)

        lbl_pitch = QLabel("Pitch:")
        self.spin_pitch = QDoubleSpinBox()
        self.spin_pitch.setRange(-180, 180)
        self.spin_pitch.setDecimals(2)
        self.spin_pitch.setValue(0)

        lbl_roll = QLabel("Roll:")
        self.spin_roll = QDoubleSpinBox()
        self.spin_roll.setRange(-180, 180)
        self.spin_roll.setDecimals(2)
        self.spin_roll.setValue(0)

        btn_rotacao = QPushButton("Aplicar Rotacao")
        btn_rotacao.clicked.connect(self.aplicar_rotacao)

        btn_animate = QPushButton("Animação")
        btn_animate.clicked.connect(self.toggle_animation)

        rot_layout.addWidget(lbl_yaw, 0, 0)
        rot_layout.addWidget(self.spin_yaw, 0, 1)
        rot_layout.addWidget(lbl_pitch, 1, 0)
        rot_layout.addWidget(self.spin_pitch, 1, 1)
        rot_layout.addWidget(lbl_roll, 2, 0)
        rot_layout.addWidget(self.spin_roll, 2, 1)
        rot_layout.addWidget(btn_rotacao, 3, 0, 1, 2)
        rot_layout.addWidget(btn_animate, 4, 0, 1, 2)

        # Painel direito
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        main_layout.addWidget(right_panel, 1)

        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.ax.set_title("Trajetória do Aeromodelo")
        self.ax.set_xlabel("Longitude")
        self.ax.set_ylabel("Latitude")
        self.ax.grid(True)
        self.canvas = FigureCanvas(self.fig)
        right_layout.addWidget(self.canvas, 4)

        traj_controls = QWidget()
        traj_layout = QGridLayout(traj_controls)
        right_layout.addWidget(traj_controls, 1)

        lbl_lat = QLabel("Latitude:")
        self.edit_lat = QLineEdit()
        lbl_lon = QLabel("Longitude:")
        self.edit_lon = QLineEdit()

        btn_add = QPushButton("Adicionar Ponto")
        btn_add.clicked.connect(self.add_point)
        btn_abrir_maps = QPushButton("Abrir no Google Maps")
        btn_abrir_maps.clicked.connect(self.abrir_no_google_maps)
        btn_salvar = QPushButton("Salvar Trajetória")
        btn_salvar.clicked.connect(self.salvar_trajetoria)

        traj_layout.addWidget(lbl_lat, 0, 0)
        traj_layout.addWidget(self.edit_lat, 0, 1)
        traj_layout.addWidget(lbl_lon, 1, 0)
        traj_layout.addWidget(self.edit_lon, 1, 1)
        traj_layout.addWidget(btn_add, 2, 0, 1, 2)
        traj_layout.addWidget(btn_abrir_maps, 3, 0, 1, 2)
        traj_layout.addWidget(btn_salvar, 4, 0, 1, 2)

    def aplicar_rotacao(self):
        yaw, pitch, roll = self.spin_yaw.value(), self.spin_pitch.value(), self.spin_roll.value()
        modelo.points = modelo_original.points.copy() - centroide
        rot = R.from_euler('zyx', [yaw, pitch, roll], degrees=True).as_matrix()
        modelo.points = modelo.points @ rot.T + centroide
        self.plotter.update()

    def add_point(self):
        try:
            lat, lon = float(self.edit_lat.text()), float(self.edit_lon.text())
        except ValueError:
            QMessageBox.warning(self, "Erro", "Valores inválidos!")
            return
        
        if not self.trajectory or (lat, lon) != self.trajectory[-1]:
            self.trajectory.append((lat, lon))
            self.update_plot()

    def update_plot(self):
        self.ax.clear()
        self.ax.set_title("Trajetória do Aeromodelo")
        self.ax.set_xlabel("Longitude")
        self.ax.set_ylabel("Latitude")
        self.ax.grid(True)
        if self.trajectory:
            lons, lats = zip(*self.trajectory)
            self.ax.plot(lons, lats, 'b-', linewidth=2)
        self.canvas.draw()

    def abrir_no_google_maps(self):
        if self.trajectory:
            lat, lon = self.trajectory[-1]
            webbrowser.open(f"https://www.google.com/maps?q={lat},{lon}")

    def salvar_trajetoria(self):
        self.fig.savefig("trajetoria.png")
        QMessageBox.information(self, "Salvo", "Trajetória salva com sucesso!")

    def toggle_animation(self):
        if self.animating:
            self.animation_timer.stop()
        else:
            self.animation_timer.start(100)
        self.animating = not self.animating

    def animate_rotation(self):
        self.animation_step += 5
        self.spin_yaw.setValue(np.sin(np.radians(self.animation_step)) * 45)
        self.spin_pitch.setValue(np.cos(np.radians(self.animation_step)) * 30)
        self.aplicar_rotacao()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())