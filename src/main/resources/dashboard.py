import os
import sys
import math
import time
import queue
import threading
from collections import deque

import numpy as np
import pyvista as pv
import serial
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QGroupBox,
    QProgressBar, QSizePolicy, QTextEdit
)
from pyvistaqt import QtInteractor

from util.XboxController import XboxController

# ── Configurações ────────────────────────────────────────────────────
SERIAL_PORT  = 'COM4'
SERIAL_BAUD  = 115200
MODELO_PATH  = "C:/Users/danie/Desktop/Programacao/Aviao_Inteligente/src/main/resources/modelo.obj"
CONTROL_INTERVAL_MS  = 20    # 50 Hz — controle (prioridade máxima)
QUEUE_DRAIN_MS       = 10    # drena fila de telemetria (só parsing + labels, SEM render)
RENDER_3D_INTERVAL   = 0.05  # s — render do modelo 3D, máx 20 Hz
PLOT_INTERVAL        = 0.50  # s — redraw do matplotlib, máx 2 Hz
QUALITY_INTERVAL_MS  = 1000
TRAJECTORY_MAX       = 4000

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


def _pop_lines(buf: bytes):
    """Extrai linhas completas de um buffer de bytes — sem instanciar objetos extras."""
    lines = []
    parts = buf.split(b'\n')
    buf = parts[-1]
    for raw in parts[:-1]:
        line = raw.replace(b'\r', b'').strip()
        if line:
            lines.append(line)
    return lines, buf


def map_axis_centered(axis: float) -> int:
    if abs(axis) < 0.08:
        axis = 0.0
    return int(round(50 + max(-1.0, min(1.0, axis)) * 50))


def map_trigger(value: float) -> int:
    if value < 0.08:
        value = 0.0
    return int(round(min(1.0, value) * 100))


DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1b1e26;
    color: #e6e6e6;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #343a48;
    border-radius: 8px;
    margin-top: 10px;
    padding: 10px;
    font-weight: 600;
    color: #8fb8ff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}
QLineEdit {
    background-color: #11141a;
    border: 1px solid #343a48;
    border-radius: 5px;
    padding: 4px 6px;
    color: #e6e6e6;
}
QPushButton {
    background-color: #2a3142;
    border: 1px solid #3d4659;
    border-radius: 6px;
    padding: 6px 12px;
    color: #e6e6e6;
}
QPushButton:hover  { background-color: #364056; }
QPushButton:pressed { background-color: #222838; }
QProgressBar {
    background-color: #11141a;
    border: 1px solid #343a48;
    border-radius: 5px;
    text-align: center;
    color: #e6e6e6;
    height: 16px;
}
QProgressBar::chunk { background-color: #4f8cff; border-radius: 5px; }
QTextEdit {
    background-color: #11141a;
    border: 1px solid #343a48;
    border-radius: 5px;
}
QLabel#bigStatus { font-size: 13px; font-weight: 600; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard de Voo — Aeromodelo Inteligente")
        self.resize(1500, 880)
        self.setStyleSheet(DARK_STYLE)

        # ── Estado ──────────────────────────────────────────────────
        self.trajectory = deque(maxlen=TRAJECTORY_MAX)
        self.ser = None

        # Fila entre thread de leitura serial e thread principal do Qt
        self._telem_queue = queue.Queue()
        self._running = True           # flag de encerramento para a thread
        self._ser_lock = threading.Lock()  # protege self.ser de acesso concorrente

        # Estado de telemetria — só escrito pela thread principal
        self._pkt_count   = 0
        self._last_rx_t   = None
        self._latency_ms  = None

        # Dados de render pendentes — setados no drain, consumidos no render timer
        # (evita render por dentro do loop de drain, que bloquearia o main thread)
        self._pending_rotation = None   # (roll, pitch, yaw) mais recente
        self._plot_dirty = False        # True = há pontos novos no mapa
        self._last_3d_t  = 0.0         # timestamp do último render 3D
        self._last_plot_t = 0.0        # timestamp do último draw do matplotlib

        # ── Build UI ────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # Coluna esquerda
        left_col = QVBoxLayout()
        root.addLayout(left_col, 3)

        cad_group = QGroupBox("Atitude (modelo 3D)")
        cad_layout = QVBoxLayout(cad_group)
        self.plotter = QtInteractor(self)
        self.plotter.add_mesh(modelo, color="white")
        self.plotter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cad_layout.addWidget(self.plotter, 6)

        attitude_readout = QGridLayout()
        self.lbl_roll  = QLabel("Roll: --- °")
        self.lbl_pitch = QLabel("Pitch: --- °")
        self.lbl_yaw   = QLabel("Yaw: --- °")
        for i, lbl in enumerate((self.lbl_roll, self.lbl_pitch, self.lbl_yaw)):
            lbl.setObjectName("bigStatus")
            attitude_readout.addWidget(lbl, 0, i)
        cad_layout.addLayout(attitude_readout)
        left_col.addWidget(cad_group, 6)

        control_group = QGroupBox("Controle enviado (0–100)")
        control_layout = QGridLayout(control_group)
        self.bar_throttle = QProgressBar()
        self.bar_aileron  = QProgressBar()
        self.bar_rudder   = QProgressBar()
        self.bar_elevator = QProgressBar()
        for bar in (self.bar_throttle, self.bar_aileron, self.bar_rudder, self.bar_elevator):
            bar.setRange(0, 100)
            bar.setValue(0)
        control_layout.addWidget(QLabel("Motor"),     0, 0)
        control_layout.addWidget(self.bar_throttle,   0, 1)
        control_layout.addWidget(QLabel("Aileron"),   1, 0)
        control_layout.addWidget(self.bar_aileron,    1, 1)
        control_layout.addWidget(QLabel("Leme"),      2, 0)
        control_layout.addWidget(self.bar_rudder,     2, 1)
        control_layout.addWidget(QLabel("Profundor"), 3, 0)
        control_layout.addWidget(self.bar_elevator,   3, 1)
        left_col.addWidget(control_group, 1)

        # Coluna direita
        right_col = QVBoxLayout()
        root.addLayout(right_col, 2)

        conn_group = QGroupBox("Conexão")
        conn_layout = QGridLayout(conn_group)
        self.edit_com = QLineEdit(SERIAL_PORT)
        btn_serial = QPushButton("Conectar")
        btn_serial.clicked.connect(self.connect_serial)
        conn_layout.addWidget(QLabel("Porta Serial:"), 0, 0)
        conn_layout.addWidget(self.edit_com,            0, 1)
        conn_layout.addWidget(btn_serial,               0, 2)
        self.lbl_conn    = QLabel("● Desconectado")
        self.lbl_latency = QLabel("Latência: ---")
        self.lbl_quality = QLabel("Qualidade: ---")
        for lbl in (self.lbl_conn, self.lbl_latency, self.lbl_quality):
            lbl.setStyleSheet("color: gray;")
        conn_layout.addWidget(self.lbl_conn,    1, 0)
        conn_layout.addWidget(self.lbl_latency, 1, 1)
        conn_layout.addWidget(self.lbl_quality, 1, 2)
        right_col.addWidget(conn_group)

        telem_group = QGroupBox("Telemetria de voo")
        telem_layout = QGridLayout(telem_group)
        self.lbl_alt   = QLabel("Altitude: --- m")
        self.lbl_speed = QLabel("Velocidade: --- km/h")
        self.lbl_fix   = QLabel("Fix: ---")
        self.lbl_sv    = QLabel("Satélites: ---")
        telem_layout.addWidget(self.lbl_alt,   0, 0)
        telem_layout.addWidget(self.lbl_speed, 0, 1)
        telem_layout.addWidget(self.lbl_fix,   1, 0)
        telem_layout.addWidget(self.lbl_sv,    1, 1)
        right_col.addWidget(telem_group)

        traj_group = QGroupBox("Trajetória (metros, relativa ao home)")
        traj_layout = QVBoxLayout(traj_group)
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.fig.patch.set_facecolor("#1b1e26")
        self.ax.set_facecolor("#11141a")
        self._style_axes()
        self.canvas = FigureCanvas(self.fig)
        traj_layout.addWidget(self.canvas, 5)
        traj_btns = QHBoxLayout()
        btn_salvar = QPushButton("Salvar imagem")
        btn_limpar = QPushButton("Limpar trajetória")
        btn_salvar.clicked.connect(self.salvar_trajetoria)
        btn_limpar.clicked.connect(self.limpar_trajetoria)
        traj_btns.addWidget(btn_salvar)
        traj_btns.addWidget(btn_limpar)
        traj_layout.addLayout(traj_btns)
        right_col.addWidget(traj_group, 4)

        log_group = QGroupBox("Eventos")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(90)
        log_layout.addWidget(self.log_text)
        right_col.addWidget(log_group)

        # ── Controller ──────────────────────────────────────────────
        try:
            self.controller = XboxController()
            self.log("Controle Xbox detectado", "#7CFC9A")
        except Exception as e:
            self.controller = None
            self.log(f"Erro ao inicializar controle: {e}", "#ff7a7a")

        # ── Serial ──────────────────────────────────────────────────
        self._open_serial(SERIAL_PORT)

        # ── Thread de leitura serial ─────────────────────────────────
        # Roda fora do Qt — coloca linhas brutas na fila, nunca toca na UI.
        self._reader_thread = threading.Thread(
            target=self._serial_reader, daemon=True, name="serial-reader"
        )
        self._reader_thread.start()

        # ── Timers ──────────────────────────────────────────────────
        # Controle (prioridade máxima — nunca bloqueado por I/O ou render)
        self.control_timer = QTimer()
        self.control_timer.timeout.connect(self.send_control)
        self.control_timer.start(CONTROL_INTERVAL_MS)

        # Drain da fila: apenas parsing + atualização de labels (< 1ms/tick)
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self._drain_queue)
        self.queue_timer.start(QUEUE_DRAIN_MS)

        # Render 3D + matplotlib a taxa controlada (sem competir com controle)
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self._throttled_render)
        self.render_timer.start(int(RENDER_3D_INTERVAL * 1000))

        self.quality_timer = QTimer()
        self.quality_timer.timeout.connect(self.update_quality_labels)
        self.quality_timer.start(QUALITY_INTERVAL_MS)

    # ── Log ─────────────────────────────────────────────────────────
    def log(self, msg: str, color: str = "#e6e6e6"):
        self.log_text.append(f'<span style="color:{color}">{msg}</span>')

    # ── Serial ──────────────────────────────────────────────────────
    def _open_serial(self, port: str):
        with self._ser_lock:
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
                s.dtr      = False
                s.rts      = False
                s.open()
                self.ser = s
                self.log(f"Serial aberta: {port}", "#7CFC9A")
            except Exception as e:
                self.ser = None
                self.log(f"Serial não disponível ({e})", "#ff7a7a")

    def connect_serial(self):
        port = self.edit_com.text().strip()
        if port:
            self._open_serial(port)

    # ── Thread de leitura serial ─────────────────────────────────────
    def _serial_reader(self):
        """Roda em background. Única responsabilidade: bytes -> linhas -> fila.
        Nunca acessa widgets Qt. Lock em torno de self.ser para segurança."""
        buf = b""
        while self._running:
            with self._ser_lock:
                ser = self.ser
            if ser is None or not ser.is_open:
                time.sleep(0.05)
                continue
            try:
                n = ser.in_waiting
                if n:
                    buf += ser.read(n)
                    lines, buf = _pop_lines(buf)
                    for line in lines:
                        self._telem_queue.put_nowait(line)
            except Exception:
                with self._ser_lock:
                    self.ser = None
            time.sleep(0.005)   # 200Hz de polling — headroom suficiente para 50Hz

    # ── Drain da fila (thread principal, 10ms) ───────────────────────
    def _drain_queue(self):
        """Consome até 30 linhas por tick. Só faz parsing e atualiza
        labels de texto — sem render 3D nem matplotlib."""
        for _ in range(30):
            try:
                raw = self._telem_queue.get_nowait()
            except queue.Empty:
                break
            self._process_line(raw)

    def _process_line(self, raw: bytes):
        try:
            parts = raw.decode(errors="ignore").split(",")
            if len(parts) != 10:
                return
            roll  = float(parts[0])
            pitch = -float(parts[1])
            yaw   = -float(parts[2])
            lon_d = int(parts[3])
            lat_d = int(parts[4])
            alt   = float(parts[5])
            speed = int(parts[6])
            fix   = int(parts[7])
            sats  = int(parts[8])
            rtt   = int(parts[9])
        except (ValueError, IndexError):
            return

        if not all(_is_finite(v) for v in (roll, pitch, yaw, alt)):
            return

        # Marca rotação pendente (render ocorre no timer separado)
        self._pending_rotation = (roll, pitch, yaw)

        # Labels são operações baratas — ok no drain
        self.lbl_roll.setText(f"Roll: {roll:.1f} °")
        self.lbl_pitch.setText(f"Pitch: {pitch:.1f} °")
        self.lbl_yaw.setText(f"Yaw: {yaw:.1f} °")
        fix_txt = {0: "sem fix", 2: "2D", 3: "3D"}.get(fix, str(fix))
        self.lbl_alt.setText(f"Altitude: {alt:.1f} m")
        self.lbl_speed.setText(f"Velocidade: {speed} km/h")
        self.lbl_fix.setText(f"Fix: {fix_txt}")
        self.lbl_sv.setText(f"Satélites: {sats}")

        self._latency_ms  = rtt
        self._pkt_count  += 1
        self._last_rx_t   = time.time()

        if fix >= 3:
            self.trajectory.append((lon_d, lat_d))
            self._plot_dirty = True

    # ── Render throttled (50ms timer = máx 20Hz) ────────────────────
    def _throttled_render(self):
        now = time.time()

        # 3D: aplica apenas a última rotação acumulada desde o tick anterior
        if self._pending_rotation is not None and now - self._last_3d_t >= RENDER_3D_INTERVAL:
            self._aplicar_rotacao(*self._pending_rotation)
            self._pending_rotation = None
            self._last_3d_t = now

        # Matplotlib: redesenha só quando há dados novos e o intervalo passou
        if self._plot_dirty and now - self._last_plot_t >= PLOT_INTERVAL:
            self._update_plot()
            self._plot_dirty = False
            self._last_plot_t = now

    # ── Qualidade ────────────────────────────────────────────────────
    def update_quality_labels(self):
        pps = self._pkt_count
        self._pkt_count = 0
        connected = self._last_rx_t is not None and time.time() - self._last_rx_t < 1.5
        if connected:
            q = min(100, int(pps / 50 * 100))
            color = "#7CFC9A" if q >= 70 else "#ffb86c" if q >= 30 else "#ff7a7a"
            self.lbl_conn.setText("● Conectado")
            self.lbl_conn.setStyleSheet(f"color: {color};")
            self.lbl_quality.setText(f"Qualidade: {pps} pkt/s ({q}%)")
            self.lbl_quality.setStyleSheet(f"color: {color};")
        else:
            self.lbl_conn.setText("● Desconectado")
            self.lbl_conn.setStyleSheet("color: #ff7a7a;")
            self.lbl_quality.setText("Qualidade: ---")
            self.lbl_quality.setStyleSheet("color: gray;")
        if self._latency_ms is not None:
            lat_color = ("#7CFC9A" if self._latency_ms < 50 else
                         "#ffb86c" if self._latency_ms < 200 else "#ff7a7a")
            self.lbl_latency.setText(f"Latência: {self._latency_ms:.0f} ms")
            self.lbl_latency.setStyleSheet(f"color: {lat_color};")

    # ── Envio de controle ─────────────────────────────────────────────
    def send_control(self):
        """Timer de 20ms. Nunca bloqueado por I/O ou render — a leitura
        serial está em thread separada e os renders têm seus próprios timers."""
        if not self.controller:
            return
        with self._ser_lock:
            ser = self.ser
        if ser is None or not ser.is_open:
            return
        try:
            throttle = map_trigger(-self.controller.getRightTrigger())
            aileron  = map_axis_centered(self.controller.getLeftX())
            rudder   = map_axis_centered(self.controller.getRightX())
            elevator = map_axis_centered(self.controller.getRightY())
            ser.write(f"{throttle},{aileron},{rudder},{elevator}\n".encode())
            self.bar_throttle.setValue(throttle)
            self.bar_aileron.setValue(aileron)
            self.bar_rudder.setValue(rudder)
            self.bar_elevator.setValue(elevator)
        except Exception as e:
            self.log(f"Erro enviando controle: {e}", "#ff7a7a")
            with self._ser_lock:
                self.ser = None

    # ── Render 3D ────────────────────────────────────────────────────
    def _aplicar_rotacao(self, roll_deg: float, pitch_deg: float, yaw_deg: float):
        yaw   = math.radians(yaw_deg)
        pitch = math.radians(pitch_deg)
        roll  = math.radians(roll_deg)
        Rx = np.array([[1, 0,              0              ],
                       [0, math.cos(roll), -math.sin(roll)],
                       [0, math.sin(roll),  math.cos(roll)]])
        Ry = np.array([[ math.cos(pitch), 0, math.sin(pitch)],
                       [ 0,               1, 0              ],
                       [-math.sin(pitch), 0, math.cos(pitch)]])
        Rz = np.array([[math.cos(yaw), -math.sin(yaw), 0],
                       [math.sin(yaw),  math.cos(yaw), 0],
                       [0,              0,             1]])
        pts = modelo_original.points.copy() - centroide
        modelo.points = (pts @ (Rz @ Ry @ Rx).T) + centroide
        try:
            self.plotter.update()
            self.plotter.render()
        except Exception:
            pass

    # ── Trajetória ────────────────────────────────────────────────────
    def _style_axes(self):
        self.ax.clear()
        self.ax.set_facecolor("#11141a")
        self.ax.set_title("Trajetória", color="#e6e6e6")
        self.ax.set_xlabel("Leste (m)", color="#e6e6e6")
        self.ax.set_ylabel("Norte (m)", color="#e6e6e6")
        self.ax.tick_params(colors="#9aa3b5")
        self.ax.grid(True, color="#2a3142")

    def _update_plot(self):
        self._style_axes()
        if self.trajectory:
            east, north = zip(*self.trajectory)
            self.ax.plot(east, north, color="#4f8cff", linewidth=2)
            self.ax.plot(east[-1], north[-1], "o", color="#7CFC9A", markersize=6)
        self.canvas.draw_idle()   # agenda o repaint sem bloquear o event loop

    def limpar_trajetoria(self):
        self.trajectory.clear()
        self._plot_dirty = True

    def salvar_trajetoria(self):
        self.fig.savefig("trajetoria.png", facecolor=self.fig.get_facecolor())
        self.log("Trajetória salva em trajetoria.png", "#7CFC9A")

    # ── Encerramento ──────────────────────────────────────────────────
    def closeEvent(self, event):
        self._running = False          # sinaliza thread para sair
        self._reader_thread.join(timeout=1.0)
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())