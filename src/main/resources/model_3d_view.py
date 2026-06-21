"""Encapsula o QtInteractor (pyvista) e a rotação do modelo 3D a partir
de roll/pitch/yaw. Mantém a mesma matemática de rotação do projeto
original (Rz @ Ry @ Rx aplicada em torno do centróide)."""
import math

import numpy as np
from PyQt5.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from pyvistaqt import QtInteractor


class Model3DView(QWidget):
    def __init__(self, mesh_original, parent=None):
        super().__init__(parent)
        self.mesh_original = mesh_original
        self.mesh = mesh_original.copy()
        self.centroid = mesh_original.points.mean(axis=0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plotter = QtInteractor(self)
        self.plotter.add_mesh(self.mesh, color="white")
        self.plotter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.plotter)

    def set_orientation(self, roll_deg: float, pitch_deg: float, yaw_deg: float):
        roll = math.radians(roll_deg)
        pitch = math.radians(pitch_deg)
        yaw = math.radians(yaw_deg)

        Rx = np.array([
            [1, 0, 0],
            [0, math.cos(roll), -math.sin(roll)],
            [0, math.sin(roll), math.cos(roll)],
        ])
        Ry = np.array([
            [math.cos(pitch), 0, math.sin(pitch)],
            [0, 1, 0],
            [-math.sin(pitch), 0, math.cos(pitch)],
        ])
        Rz = np.array([
            [math.cos(yaw), -math.sin(yaw), 0],
            [math.sin(yaw), math.cos(yaw), 0],
            [0, 0, 1],
        ])
        rotation_matrix = Rz @ Ry @ Rx

        pts = self.mesh_original.points.copy() - self.centroid
        self.mesh.points = (pts @ rotation_matrix.T) + self.centroid

        try:
            self.plotter.update()
            self.plotter.render()
        except Exception:
            # falha pontual de render não deve derrubar a aplicação
            pass