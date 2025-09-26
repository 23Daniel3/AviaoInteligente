import os
import sys
import math
import socket
import numpy as np
import pyvista as pv
import webbrowser
import matplotlib
from PyQt5.QtCore import QTimer, Qt
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QDoubleSpinBox, QLineEdit, QPushButton,
    QMessageBox, QSizePolicy, QTextEdit, QTabWidget
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from pyvistaqt import QtInteractor
from util.XboxController import XboxController  # ✅ Import do controle

# Caminho do modelo CAD
modelo_path = "C:/Users/danie/Desktop/Programacao/Aviao_Inteligente/src/main/resources/modelo.obj"
if not os.path.exists(modelo_path):
    print(f"Erro: Arquivo {modelo_path} não encontrado!")
    sys.exit(1)

modelo_original = pv.read(modelo_path)
modelo = modelo_original.copy()
centroide = modelo.points.mean(axis=0)


def _is_finite(x):
    try:
        return math.isfinite(x)
    except Exception:
        return False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard de Monitoramento")
        self.resize(1600, 900)

        self.trajectory = []

        # Conexões TCP
        self.esp32_ip = "192.168.4.1"
        self.gyro_sock = None
        self.log_sock = None
        self.control_sock = None
        self.gyro_buf = b""
        self.log_buf = b""

        # ✅ Criar tabs primeiro (incluindo aba de log)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Aba de Log (precisa vir antes do uso de self.log)
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        self.tabs.addTab(self.log_tab, "Log de Conexão")

        # Xbox Controller (agora pode chamar self.log sem erro)
        try:
            self.controller = XboxController()
            self.log("✅ Controle Xbox detectado", "green")
        except Exception as e:
            self.controller = None
            self.log(f"❌ Erro ao inicializar controle: {e}", "red")


        # Timer de conexão
        self.connect_timer = QTimer()
        self.connect_timer.timeout.connect(self.try_connect)
        self.connect_timer.start(3000)

        # Timer de leitura dos dados do ESP32
        self.gyro_timer = QTimer()
        self.gyro_timer.timeout.connect(self.read_gyro)
        self.gyro_timer.start(2)

        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.read_logs)
        self.log_timer.start(200)

        # Timer para envio do controle Xbox
        self.control_timer = QTimer()
        self.control_timer.timeout.connect(self.send_control)
        self.control_timer.start(10)  # ~20 Hz

        # Tabs principais
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Aba Dashboard
        dashboard_tab = QWidget()
        main_layout = QHBoxLayout(dashboard_tab)
        self.tabs.addTab(dashboard_tab, "Dashboard")

        # Painel esquerdo
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        main_layout.addWidget(left_panel, 3)

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

        lbl_pitch = QLabel("Pitch:")
        self.spin_pitch = QDoubleSpinBox()
        self.spin_pitch.setRange(-180, 180)
        self.spin_pitch.setDecimals(2)

        lbl_roll = QLabel("Roll:")
        self.spin_roll = QDoubleSpinBox()
        self.spin_roll.setRange(-180, 180)
        self.spin_roll.setDecimals(2)

        rot_layout.addWidget(lbl_yaw, 0, 0)
        rot_layout.addWidget(self.spin_yaw, 0, 1)
        rot_layout.addWidget(lbl_pitch, 1, 0)
        rot_layout.addWidget(self.spin_pitch, 1, 1)
        rot_layout.addWidget(lbl_roll, 2, 0)
        rot_layout.addWidget(self.spin_roll, 2, 1)

        # Painel direito
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        main_layout.addWidget(right_panel, 1)

        # Campo para definir IP do ESP32
        ip_layout = QHBoxLayout()
        lbl_ip = QLabel("IP ESP32:")
        self.edit_ip = QLineEdit(self.esp32_ip)
        btn_set_ip = QPushButton("Aplicar IP")
        btn_set_ip.clicked.connect(self.set_ip)
        ip_layout.addWidget(lbl_ip)
        ip_layout.addWidget(self.edit_ip)
        ip_layout.addWidget(btn_set_ip)
        right_layout.addLayout(ip_layout)

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

        # Aba de Log
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        self.tabs.addTab(self.log_tab, "Log de Conexão")

    def set_ip(self):
        new_ip = self.edit_ip.text().strip()
        if new_ip:
            self.esp32_ip = new_ip
            self.close_sockets()
            self.log(f"🔄 IP definido para {self.esp32_ip}. Tentando conectar...", "blue")

    def log(self, msg, color="black"):
        self.log_text.append(f'<span style="color:{color}">{msg}</span>')

    def try_connect(self):
        if not self.gyro_sock:
            try:
                self.gyro_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.gyro_sock.settimeout(1)
                self.gyro_sock.connect((self.esp32_ip, 8080))
                self.gyro_sock.setblocking(False)
                self.log("✅ Conectado ao socket de giroscópio (8080)", "green")
            except Exception as e:
                self.gyro_sock = None
                self.log(f"❌ Erro ao conectar giroscópio: {e}", "red")

        if not self.log_sock:
            try:
                self.log_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.log_sock.settimeout(1)
                self.log_sock.connect((self.esp32_ip, 9090))
                self.log_sock.setblocking(False)
                self.log("✅ Conectado ao socket de logs (9090)", "green")
            except Exception as e:
                self.log_sock = None
                self.log(f"❌ Erro ao conectar logs: {e}", "red")

        if not self.control_sock:
            try:
                self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.control_sock.settimeout(1)
                self.control_sock.connect((self.esp32_ip, 10000))
                self.control_sock.setblocking(False)
                self.log("✅ Conectado ao socket de controle (10000)", "green")
            except Exception as e:
                self.control_sock = None
                self.log(f"❌ Erro ao conectar controle: {e}", "red")

    def close_sockets(self):
        for sock in [self.gyro_sock, self.log_sock, self.control_sock]:
            if sock:
                try: sock.close()
                except: pass
        self.gyro_sock = None
        self.log_sock = None
        self.control_sock = None

    def _pop_lines(self, buf):
        lines = []
        if not buf:
            return lines, buf
        parts = buf.split(b'\n')
        complete = parts[:-1]
        buf = parts[-1]
        for raw in complete:
            line = raw.replace(b'\r', b'').strip()
            if line:
                lines.append(line)
        return lines, buf

    def read_gyro(self):
        if not self.gyro_sock:
            return
        try:
            data = self.gyro_sock.recv(1024)
            if not data:
                return
            self.gyro_buf += data
            lines, self.gyro_buf = self._pop_lines(self.gyro_buf)
            for raw in lines:
                try:
                    line = raw.decode(errors="ignore")
                    parts = line.split(",")
                    if len(parts) != 3:
                        continue
                    roll, pitch, yaw = map(float, parts)
                    if not (_is_finite(roll) and _is_finite(pitch) and _is_finite(yaw)):
                        continue
                    self.spin_roll.setValue(roll)
                    self.spin_pitch.setValue(pitch)
                    self.spin_yaw.setValue(yaw)
                    self.aplicar_rotacao()
                except Exception as e:
                    self.log(f"⚠️ Erro processando gyro: {e}", "orange")
        except BlockingIOError:
            pass
        except Exception as e:
            self.log(f"❌ Conexão perdida giroscópio: {e}", "red")
            self.gyro_sock = None

    def read_logs(self):
        if not self.log_sock:
            return
        try:
            data = self.log_sock.recv(1024)
            if not data:
                return
            self.log_buf += data
            lines, self.log_buf = self._pop_lines(self.log_buf)
            for raw in lines:
                try:
                    line = raw.decode(errors="ignore")
                    self.log(line, "black")
                except:
                    pass
        except BlockingIOError:
            pass
        except Exception as e:
            self.log(f"❌ Conexão perdida logs: {e}", "red")
            self.log_sock = None

    def send_control(self):
        if not self.control_sock or not self.controller:
            return
        try:
            val = self.controller.getRightX()  # entre -1 e 1
            msg = f"{val}\n"
            self.control_sock.sendall(msg.encode("utf-8"))
        except Exception as e:
            self.log(f"⚠️ Erro enviando controle: {e}", "orange")
            self.control_sock = None

    def aplicar_rotacao(self):
        yaw_deg = self.spin_yaw.value()
        pitch_deg = self.spin_pitch.value()
        roll_deg = self.spin_roll.value()

        yaw = math.radians(yaw_deg)
        pitch = math.radians(pitch_deg)
        roll = math.radians(roll_deg)

        Rx = np.array([[1, 0, 0],
                    [0, math.cos(roll), -math.sin(roll)],
                    [0, math.sin(roll),  math.cos(roll)]])

        Ry = np.array([[ math.cos(pitch), 0, math.sin(pitch)],
                    [ 0,               1, 0              ],
                    [-math.sin(pitch), 0, math.cos(pitch)]])

        Rz = np.array([[math.cos(yaw), -math.sin(yaw), 0],
                    [math.sin(yaw),  math.cos(yaw), 0],
                    [0,               0,            1]])

        Rmat = Rz @ Ry @ Rx

        pts = modelo_original.points.copy() - centroide
        modelo.points = (pts @ Rmat.T) + centroide

        try:
            self.plotter.update()
            self.plotter.render()
        except Exception:
            pass

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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
