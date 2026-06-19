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
from util.XboxController import XboxController
import serial

# ── Configurações ────────────────────────────────────────────────────
SERIAL_PORT  = 'COM4'    # ← troque pela porta do transmissor ESP32
SERIAL_BAUD  = 115200
MODELO_PATH  = "C:/Users/danie/Desktop/Programacao/Aviao_Inteligente/src/main/resources/modelo.obj"

if not os.path.exists(MODELO_PATH):
    print(f"Erro: Arquivo {MODELO_PATH} não encontrado!")
    sys.exit(1)

modelo_original = pv.read(MODELO_PATH)
modelo          = modelo_original.copy()
centroide       = modelo.points.mean(axis=0)


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

        # Conexões TCP (giroscópio + logs via WiFi do ESP32-S3)
        self.esp32_ip  = "192.168.4.1"
        self.gyro_sock = None
        self.log_sock  = None
        self.gyro_buf  = b""
        self.log_buf   = b""

        # ── Tabs (criado UMA VEZ, aqui) ──────────────────────────────
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Aba Dashboard
        dashboard_tab = QWidget()
        main_layout   = QHBoxLayout(dashboard_tab)
        self.tabs.addTab(dashboard_tab, "Dashboard")

        # Aba de Log — precisa existir ANTES do primeiro self.log()
        log_tab        = QWidget()
        log_layout     = QVBoxLayout(log_tab)
        self.log_text  = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        self.tabs.addTab(log_tab, "Log de Conexão")

        # ── Xbox Controller ──────────────────────────────────────────
        try:
            self.controller = XboxController()
            self.log("✅ Controle Xbox detectado", "green")
        except Exception as e:
            self.controller = None
            self.log(f"❌ Erro ao inicializar controle: {e}", "red")

        # ── Serial para o transmissor ESP32 (USB) ────────────────────
        self.ser = None
        self._open_serial(SERIAL_PORT)

        # ── Timers ───────────────────────────────────────────────────
        self.connect_timer = QTimer()
        self.connect_timer.timeout.connect(self.try_connect)
        self.connect_timer.start(3000)

        self.gyro_timer = QTimer()
        self.gyro_timer.timeout.connect(self.read_gyro)
        self.gyro_timer.start(2)

        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.read_logs)
        self.log_timer.start(200)

        # 50 Hz — sincronizado com o delay(20) do transmissor
        self.control_timer = QTimer()
        self.control_timer.timeout.connect(self.send_control)
        self.control_timer.start(20)

        # ── Painel esquerdo (modelo 3D + sliders de rotação) ─────────
        left_panel  = QWidget()
        left_layout = QVBoxLayout(left_panel)
        main_layout.addWidget(left_panel, 3)

        self.plotter = QtInteractor(self)
        self.plotter.add_mesh(modelo, color="white")
        self.plotter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.plotter, 5)

        rot_group  = QWidget()
        rot_layout = QGridLayout(rot_group)
        left_layout.addWidget(rot_group, 1)

        lbl_yaw        = QLabel("Yaw:")
        self.spin_yaw  = QDoubleSpinBox()
        self.spin_yaw.setRange(-180, 180)
        self.spin_yaw.setDecimals(2)

        lbl_pitch        = QLabel("Pitch:")
        self.spin_pitch  = QDoubleSpinBox()
        self.spin_pitch.setRange(-180, 180)
        self.spin_pitch.setDecimals(2)

        lbl_roll        = QLabel("Roll:")
        self.spin_roll  = QDoubleSpinBox()
        self.spin_roll.setRange(-180, 180)
        self.spin_roll.setDecimals(2)

        rot_layout.addWidget(lbl_yaw,        0, 0)
        rot_layout.addWidget(self.spin_yaw,  0, 1)
        rot_layout.addWidget(lbl_pitch,      1, 0)
        rot_layout.addWidget(self.spin_pitch, 1, 1)
        rot_layout.addWidget(lbl_roll,       2, 0)
        rot_layout.addWidget(self.spin_roll, 2, 1)

        # ── Painel direito (IP + trajetória) ─────────────────────────
        right_panel  = QWidget()
        right_layout = QVBoxLayout(right_panel)
        main_layout.addWidget(right_panel, 1)

        ip_layout  = QHBoxLayout()
        lbl_ip     = QLabel("IP ESP32:")
        self.edit_ip = QLineEdit(self.esp32_ip)
        btn_set_ip   = QPushButton("Aplicar IP")
        btn_set_ip.clicked.connect(self.set_ip)
        ip_layout.addWidget(lbl_ip)
        ip_layout.addWidget(self.edit_ip)
        ip_layout.addWidget(btn_set_ip)
        right_layout.addLayout(ip_layout)

        # Campo de porta serial + botão reconectar controle
        serial_layout = QHBoxLayout()
        lbl_com       = QLabel("Porta Serial:")
        self.edit_com = QLineEdit(SERIAL_PORT)
        btn_serial    = QPushButton("Conectar Serial")
        btn_serial.clicked.connect(self.connect_serial)
        serial_layout.addWidget(lbl_com)
        serial_layout.addWidget(self.edit_com)
        serial_layout.addWidget(btn_serial)
        right_layout.addLayout(serial_layout)

        btn_ctrl = QPushButton("Reconectar Controle Xbox")
        btn_ctrl.clicked.connect(self.reconnect_controller)
        right_layout.addWidget(btn_ctrl)

        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.ax.set_title("Trajetória do Aeromodelo")
        self.ax.set_xlabel("Longitude")
        self.ax.set_ylabel("Latitude")
        self.ax.grid(True)
        self.canvas = FigureCanvas(self.fig)
        right_layout.addWidget(self.canvas, 4)

        traj_controls = QWidget()
        traj_layout   = QGridLayout(traj_controls)
        right_layout.addWidget(traj_controls, 1)

        lbl_lat       = QLabel("Latitude:")
        self.edit_lat = QLineEdit()
        lbl_lon       = QLabel("Longitude:")
        self.edit_lon = QLineEdit()

        btn_add        = QPushButton("Adicionar Ponto")
        btn_abrir_maps = QPushButton("Abrir no Google Maps")
        btn_salvar     = QPushButton("Salvar Trajetória")
        btn_add.clicked.connect(self.add_point)
        btn_abrir_maps.clicked.connect(self.abrir_no_google_maps)
        btn_salvar.clicked.connect(self.salvar_trajetoria)

        traj_layout.addWidget(lbl_lat,        0, 0)
        traj_layout.addWidget(self.edit_lat,  0, 1)
        traj_layout.addWidget(lbl_lon,        1, 0)
        traj_layout.addWidget(self.edit_lon,  1, 1)
        traj_layout.addWidget(btn_add,        2, 0, 1, 2)
        traj_layout.addWidget(btn_abrir_maps, 3, 0, 1, 2)
        traj_layout.addWidget(btn_salvar,     4, 0, 1, 2)

    # ── Helpers ──────────────────────────────────────────────────────

    def set_ip(self):
        new_ip = self.edit_ip.text().strip()
        if new_ip:
            self.esp32_ip = new_ip
            self.close_sockets()
            self.log(f"🔄 IP definido para {self.esp32_ip}. Tentando conectar...", "blue")

    def _open_serial(self, port: str):
        """Abre a serial SEM tocar em DTR/RTS — evita reset do ESP32."""
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        try:
            s = serial.Serial()
            s.port     = port
            s.baudrate = SERIAL_BAUD
            s.timeout  = 0
            s.dtr      = False   # ← não reseta o ESP32 ao abrir
            s.rts      = False
            s.open()
            self.ser = s
            self.log(f"✅ Serial aberta: {port}", "green")
        except Exception as e:
            self.ser = None
            self.log(f"❌ Serial não disponível ({e}) — ajuste a porta e clique Conectar Serial", "red")

    def connect_serial(self):
        port = self.edit_com.text().strip()
        if port:
            self._open_serial(port)

    def reconnect_controller(self):
        """Re-enumera joysticks pygame sem reiniciar toda a lib."""
        try:
            import pygame
            pygame.joystick.quit()
            pygame.joystick.init()
            self.controller = XboxController()
            self.log("✅ Controle Xbox reconectado", "green")
        except Exception as e:
            self.controller = None
            self.log(f"❌ Controle não encontrado: {e}", "red")

    def log(self, msg, color="black"):
        self.log_text.append(f'<span style="color:{color}">{msg}</span>')

    # ── Conexões TCP ─────────────────────────────────────────────────

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

    def close_sockets(self):
        for sock in [self.gyro_sock, self.log_sock]:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
        self.gyro_sock = None
        self.log_sock  = None

    def _pop_lines(self, buf):
        lines = []
        if not buf:
            return lines, buf
        parts    = buf.split(b'\n')
        complete = parts[:-1]
        buf      = parts[-1]
        for raw in complete:
            line = raw.replace(b'\r', b'').strip()
            if line:
                lines.append(line)
        return lines, buf

    # ── Leitura TCP ──────────────────────────────────────────────────

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
                    line  = raw.decode(errors="ignore")
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
                    self.log(raw.decode(errors="ignore"), "black")
                except Exception:
                    pass
        except BlockingIOError:
            pass
        except Exception as e:
            self.log(f"❌ Conexão perdida logs: {e}", "red")
            self.log_sock = None

    # ── Envio de controle via Serial → transmissor ESP32 ─────────────
    #
    # Protocolo: "<motorEnabled>,<throttle>\n"
    #   motorEnabled : 0 ou 1  (leftBumper)
    #   throttle     : 1000–2000 µs
    #
    # Mapeamento do stick esquerdo Y:
    #   baixo (-1.0) → 1000   centro (0.0) → 1000   cima (1.0) → 2000
    # (stick solto / centro = motor parado — seguro por padrão)

    def send_control(self):
        if not self.ser or not self.controller:
            return
        try:
            lb  = 1 if self.controller.getLeftBumper() else 0
            raw = self.controller.getLeftY()          # [-1.0 … 1.0]
            thr = max(1000, min(2000, int(1000 + max(0.0, raw) * 1000)))
            self.ser.write(f"{lb},{thr}\n".encode())
        except Exception as e:
            self.log(f"⚠️ Erro enviando controle serial: {e}", "orange")

    # ── Rotação 3D ───────────────────────────────────────────────────

    def aplicar_rotacao(self):
        yaw   = math.radians(self.spin_yaw.value())
        pitch = math.radians(self.spin_pitch.value())
        roll  = math.radians(self.spin_roll.value())

        Rx = np.array([[1, 0,              0             ],
                       [0, math.cos(roll), -math.sin(roll)],
                       [0, math.sin(roll),  math.cos(roll)]])

        Ry = np.array([[ math.cos(pitch), 0, math.sin(pitch)],
                       [ 0,              1, 0              ],
                       [-math.sin(pitch), 0, math.cos(pitch)]])

        Rz = np.array([[math.cos(yaw), -math.sin(yaw), 0],
                       [math.sin(yaw),  math.cos(yaw), 0],
                       [0,              0,             1]])

        Rmat = Rz @ Ry @ Rx
        pts  = modelo_original.points.copy() - centroide
        modelo.points = (pts @ Rmat.T) + centroide

        try:
            self.plotter.update()
            self.plotter.render()
        except Exception:
            pass

    # ── Trajetória ───────────────────────────────────────────────────

    def add_point(self):
        try:
            lat = float(self.edit_lat.text())
            lon = float(self.edit_lon.text())
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