"""
MainWindow não contém lógica de parsing nem de socket — ela só:
  1. monta os widgets;
  2. conecta sinais do CommunicationManager a métodos _on_*;
  3. repassa dados já parseados (dataclasses) para os widgets via update_*().

Para adicionar um novo bloco de telemetria no futuro (ex.: RPM do motor):
  1. crie a dataclass em core/models.py;
  2. ensine core/telemetry.py a reconhecer a tag nova (ex.: "RPM,...");
  3. crie um widget em ui/widgets/ com um método update_rpm(data);
  4. instancie o widget aqui e trate a tag no _on_telemetry_line.
Nenhuma outra parte do sistema precisa mudar.
"""
import pyvista as pv
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

import config
from communication import CommunicationManager
from connection_state import LinkMonitor
from controller_input import ControllerInput
from models import ControlCommand, GpsFixState, PowerState
from telemetry import parse_line
from theme import build_qss
from alert_banner import AlertBanner
from battery_widget import BatteryWidget
from connection_panel import ConnectionPanel
from gps_panel import GpsPanel
from model_3d_view import Model3DView
from telemetry_panel import TelemetryPanel
from trajectory_map import TrajectoryMap
from util.XboxController import XboxController


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Estação de Controle — Aeromodelo Inteligente")
        self.resize(1700, 950)
        self.setStyleSheet(build_qss())

        self._last_command = ControlCommand()
        self._link_monitor = LinkMonitor(config.EXPECTED_PACKET_RATE_HZ, config.CONNECTION_TIMEOUT_S)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_log_tab()      # precisa existir antes do primeiro self.log()
        self._build_dashboard_tab()
        self._build_gps_tab()

        self._init_controller()
        self._init_communication()
        self._init_timers()

    # ── Construção das abas ────────────────────────────────────────

    def _build_log_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        self.tabs.addTab(tab, "Log de Conexão")

    def _build_dashboard_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)

        self.alert_banner = AlertBanner()
        outer.addWidget(self.alert_banner)

        body = QHBoxLayout()
        outer.addLayout(body, 1)

        # ── Coluna esquerda: modelo 3D + telemetria ─────────────────
        left = QVBoxLayout()
        body.addLayout(left, 3)

        if not config.MODELO_PATH.exists():
            raise FileNotFoundError(
                f"Modelo 3D não encontrado em: {config.MODELO_PATH}\n"
                f"Ajuste config.MODELO_PATH para o caminho correto."
            )
        mesh = pv.read(str(config.MODELO_PATH))
        self.model_view = Model3DView(mesh)
        left.addWidget(self.model_view, 5)

        self.telemetry_panel = TelemetryPanel()
        left.addWidget(self.telemetry_panel)

        left.addWidget(self._build_manual_debug_box())

        # ── Coluna direita: conexão, bateria, configuração ──────────
        right = QVBoxLayout()
        body.addLayout(right, 2)

        self.connection_panel = ConnectionPanel()
        right.addWidget(self.connection_panel)

        self.battery_widget = BatteryWidget()
        right.addWidget(self.battery_widget)

        right.addWidget(self._build_link_config_box())
        right.addStretch()

        self.tabs.addTab(tab, "Dashboard")

    def _build_manual_debug_box(self) -> QGroupBox:
        box = QGroupBox("Ajuste manual (debug — útil sem telemetria conectada)")
        layout = QGridLayout(box)
        self.spin_roll = QDoubleSpinBox()
        self.spin_pitch = QDoubleSpinBox()
        self.spin_yaw = QDoubleSpinBox()
        for spin in (self.spin_roll, self.spin_pitch, self.spin_yaw):
            spin.setRange(-180, 180)
            spin.setDecimals(1)
            spin.valueChanged.connect(self._on_manual_rotation)
        layout.addWidget(QLabel("Roll:"), 0, 0)
        layout.addWidget(self.spin_roll, 0, 1)
        layout.addWidget(QLabel("Pitch:"), 0, 2)
        layout.addWidget(self.spin_pitch, 0, 3)
        layout.addWidget(QLabel("Yaw:"), 0, 4)
        layout.addWidget(self.spin_yaw, 0, 5)
        return box

    def _build_link_config_box(self) -> QGroupBox:
        box = QGroupBox("Configuração de Link")
        layout = QGridLayout(box)

        layout.addWidget(QLabel("IP do ESP32:"), 0, 0)
        self.edit_ip = QLineEdit(config.ESP32_DEFAULT_IP)
        layout.addWidget(self.edit_ip, 0, 1)
        btn_ip = QPushButton("Aplicar")
        btn_ip.clicked.connect(self._on_apply_ip)
        layout.addWidget(btn_ip, 0, 2)

        layout.addWidget(QLabel("Porta Serial:"), 1, 0)
        self.edit_com = QLineEdit(config.SERIAL_PORT)
        layout.addWidget(self.edit_com, 1, 1)
        btn_serial = QPushButton("Conectar")
        btn_serial.clicked.connect(self._on_connect_serial)
        layout.addWidget(btn_serial, 1, 2)

        btn_ctrl = QPushButton("Reconectar Controle Xbox")
        btn_ctrl.clicked.connect(self._on_reconnect_controller)
        layout.addWidget(btn_ctrl, 2, 0, 1, 3)

        return box

    def _build_gps_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.gps_panel = GpsPanel()
        layout.addWidget(self.gps_panel)
        self.trajectory_map = TrajectoryMap()
        layout.addWidget(self.trajectory_map, 1)
        self.tabs.addTab(tab, "GPS & Mapa")

    # ── Inicialização ────────────────────────────────────────────────

    def _init_controller(self):
        try:
            self.controller_input = ControllerInput(XboxController())
            self.log("✅ Controle Xbox detectado", "green")
        except Exception as e:
            self.controller_input = ControllerInput(None)
            self.log(f"❌ Erro ao inicializar controle: {e}", "red")
        self.connection_panel.update_controller(self.controller_input.is_connected)

    def _init_communication(self):
        self.comm = CommunicationManager(config.ESP32_DEFAULT_IP)
        self.comm.telemetry_line.connect(self._on_telemetry_line)
        self.comm.log_line.connect(lambda line: self.log(line, "black"))
        self.comm.telemetry_status.connect(self._on_telemetry_status)
        self.comm.log_status.connect(self._on_log_status)
        self.comm.serial_status.connect(self._on_serial_status)
        self.comm.pong_received.connect(self._link_monitor.notify_pong)
        self.comm.ping_sent.connect(self._link_monitor.notify_ping_sent)
        self.comm.open_serial(config.SERIAL_PORT)

    def _init_timers(self):
        self.quality_timer = QTimer(self)
        self.quality_timer.timeout.connect(self._update_quality)
        self.quality_timer.start(config.QUALITY_UPDATE_MS)

        self.control_timer = QTimer(self)
        self.control_timer.timeout.connect(self._send_control)
        self.control_timer.start(config.CONTROL_SEND_MS)

    # ── Telemetria recebida ────────────────────────────────────────

    def _on_telemetry_line(self, raw_line: bytes):
        result = parse_line(raw_line)
        if result is None:
            return
        tag, data = result
        self._link_monitor.notify_packet()

        if tag == "IMU":
            self._apply_imu(data)
        elif tag == "BAT":
            self.battery_widget.update_battery(data)
            self._update_battery_alert(data)
        elif tag == "GPS":
            self.gps_panel.update_gps(data)
            self.trajectory_map.add_gps_point(data)
            self._update_gps_alert(data)

    def _apply_imu(self, imu):
        for spin, value in (
            (self.spin_roll, imu.roll), (self.spin_pitch, imu.pitch), (self.spin_yaw, imu.yaw)
        ):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
        self.model_view.set_orientation(imu.roll, imu.pitch, imu.yaw)
        self.telemetry_panel.update_imu(imu)

    def _on_manual_rotation(self, _value):
        self.model_view.set_orientation(
            self.spin_roll.value(), self.spin_pitch.value(), self.spin_yaw.value()
        )

    # ── Status de conexão (apenas log textual) ──────────────────────

    def _on_telemetry_status(self, ok: bool):
        self.log("✅ Conectado à telemetria (porta 8080)" if ok else
                  "❌ Telemetria desconectada (porta 8080)", "green" if ok else "red")

    def _on_log_status(self, ok: bool):
        self.log("✅ Conectado ao log (porta 9090)" if ok else
                  "❌ Log desconectado (porta 9090)", "green" if ok else "red")

    def _on_serial_status(self, ok: bool, msg: str):
        self.log(("✅ " if ok else "❌ ") + msg, "green" if ok else "red")

    # ── Qualidade / alertas ──────────────────────────────────────────

    def _update_quality(self):
        quality = self._link_monitor.sample_quality()
        self.connection_panel.update_link(quality)
        self.alert_banner.set_alert(
            "link", None if quality.connected else "Sem comunicação com o ESP32", "critico"
        )

    def _update_battery_alert(self, battery):
        if battery.state == PowerState.CRITICA:
            self.alert_banner.set_alert(
                "bateria", "Bateria em nível CRÍTICO — pouse imediatamente", "critico"
            )
        elif battery.state == PowerState.BAIXA:
            self.alert_banner.set_alert("bateria", "Bateria baixa", "atencao")
        else:
            self.alert_banner.set_alert("bateria", None)

    def _update_gps_alert(self, gps):
        if gps.fix == GpsFixState.SEM_FIX:
            self.alert_banner.set_alert("gps", "GPS sem fix", "atencao")
        else:
            self.alert_banner.set_alert("gps", None)

    # ── Ações de UI ───────────────────────────────────────────────────

    def _on_apply_ip(self):
        ip = self.edit_ip.text().strip()
        if ip:
            self.comm.set_ip(ip)
            self.log(f"🔄 IP definido para {ip}. Tentando conectar...", "blue")

    def _on_connect_serial(self):
        port = self.edit_com.text().strip()
        if port:
            self.comm.open_serial(port)

    def _on_reconnect_controller(self):
        try:
            import pygame
            pygame.joystick.quit()
            pygame.joystick.init()
            self.controller_input = ControllerInput(XboxController())
            self.log("✅ Controle Xbox reconectado", "green")
        except Exception as e:
            self.controller_input = ControllerInput(None)
            self.log(f"❌ Controle não encontrado: {e}", "red")
        self.connection_panel.update_controller(self.controller_input.is_connected)

    def _send_control(self):
        cmd = self.controller_input.read_command()
        self._last_command = cmd
        self.telemetry_panel.update_command(cmd)
        self.comm.send_control(cmd)

    # ── Util ────────────────────────────────────────────────────────

    def log(self, msg: str, color: str = "black"):
        self.log_text.append(f'<span style="color:{color}">{msg}</span>')

    def closeEvent(self, event):
        self.comm.shutdown()
        super().closeEvent(event)