"""
Tudo que toca em socket/serial fica isolado aqui. Nenhum widget conhece
o protocolo de transporte — eles só escutam os sinais Qt do
CommunicationManager. Isso permite, por exemplo, trocar TCP por outra
coisa no futuro sem tocar em uma linha de UI.

Princípio de robustez: toda operação de I/O está em try/except. Uma
falha de socket nunca propaga como exceção não tratada — ela vira um
sinal de status (conectado/desconectado) e o sistema tenta de novo
no próximo ciclo do timer de reconexão.
"""
import socket

import serial
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

import config


class _LineBuffer:
    """Acumula bytes recebidos por um socket/serial e separa em linhas \\n completas."""

    def __init__(self):
        self._buf = b""

    def feed(self, data: bytes):
        self._buf += data
        parts = self._buf.split(b"\n")
        self._buf = parts[-1]
        lines = []
        for raw in parts[:-1]:
            line = raw.replace(b"\r", b"").strip()
            if line:
                lines.append(line)
        return lines


class TcpClient:
    """Socket TCP não bloqueante com buffer de linhas e fechamento seguro."""

    def __init__(self, port: int):
        self.port = port
        self.sock = None
        self._buf = _LineBuffer()

    @property
    def is_open(self) -> bool:
        return self.sock is not None

    def connect(self, ip: str, timeout: float = 1.0) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip, self.port))
            s.setblocking(False)
            self.sock = s
            return True
        except Exception:
            self.sock = None
            return False

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None

    def send(self, data: bytes) -> bool:
        if not self.sock:
            return False
        try:
            self.sock.send(data)
            return True
        except (BlockingIOError, OSError):
            return False

    def poll_lines(self):
        """Lê o que estiver disponível agora. Fecha o socket sozinho em erro real
        (perda de conexão) — BlockingIOError (nada disponível ainda) não conta."""
        if not self.sock:
            return []
        try:
            data = self.sock.recv(2048)
            if not data:
                self.close()  # peer fechou a conexão
                return []
            return self._buf.feed(data)
        except BlockingIOError:
            return []
        except Exception:
            self.close()
            return []


class SerialClient:
    """Serial USB para o transmissor — sem tocar DTR/RTS (evita reset do ESP32)."""

    def __init__(self):
        self.ser = None

    @property
    def is_open(self) -> bool:
        return self.ser is not None and self.ser.is_open

    def open(self, port: str, baud: int) -> bool:
        self.close()
        try:
            s = serial.Serial()
            s.port = port
            s.baudrate = baud
            s.timeout = 0
            s.dtr = False
            s.rts = False
            s.open()
            self.ser = s
            return True
        except Exception:
            self.ser = None
            return False

    def close(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None

    def write_line(self, text: str) -> bool:
        if not self.is_open:
            return False
        try:
            self.ser.write(text.encode())
            return True
        except Exception:
            self.close()
            return False


class CommunicationManager(QObject):
    """
    Orquestra os três canais (telemetria TCP :8080, log TCP :9090, serial USB)
    e expõe tudo via sinais Qt — quem quiser reagir (UI, logger, gravador de
    voo, etc.) apenas se conecta ao sinal, sem acoplamento direto com sockets.
    """

    telemetry_line = pyqtSignal(bytes)      # uma linha bruta de telemetria
    log_line = pyqtSignal(str)              # uma linha de log já decodificada
    telemetry_status = pyqtSignal(bool)     # socket de telemetria abriu/fechou
    log_status = pyqtSignal(bool)           # socket de log abriu/fechou
    serial_status = pyqtSignal(bool, str)   # serial abriu/fechou + mensagem
    ping_sent = pyqtSignal()                # um PING foi enviado agora
    pong_received = pyqtSignal()            # um PONG chegou agora

    def __init__(self, esp32_ip: str, parent=None):
        super().__init__(parent)
        self.esp32_ip = esp32_ip
        self.telemetry = TcpClient(config.TELEMETRY_PORT)
        self.logs = TcpClient(config.LOG_PORT)
        self.serial = SerialClient()

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.timeout.connect(self._try_connect_sockets)
        self._reconnect_timer.start(config.RECONNECT_INTERVAL_MS)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_telemetry)
        self._poll_timer.start(config.GYRO_POLL_MS)

        self._log_poll_timer = QTimer(self)
        self._log_poll_timer.timeout.connect(self._poll_logs)
        self._log_poll_timer.start(config.LOG_POLL_MS)

        self._ping_timer = QTimer(self)
        self._ping_timer.timeout.connect(self.send_ping)
        self._ping_timer.start(config.PING_INTERVAL_MS)

        # primeira tentativa imediata, sem esperar o primeiro tick do timer
        self._try_connect_sockets()

    # ── IP / reconexão ───────────────────────────────────────────────
    def set_ip(self, ip: str):
        self.esp32_ip = ip
        self.telemetry.close()
        self.logs.close()
        self.telemetry_status.emit(False)
        self.log_status.emit(False)

    def _try_connect_sockets(self):
        if not self.telemetry.is_open:
            ok = self.telemetry.connect(self.esp32_ip)
            if ok:
                self.telemetry_status.emit(True)
        if not self.logs.is_open:
            ok = self.logs.connect(self.esp32_ip)
            if ok:
                self.log_status.emit(True)

    # ── Polling ──────────────────────────────────────────────────────
    def _poll_telemetry(self):
        if not self.telemetry.is_open:
            return
        lines = self.telemetry.poll_lines()
        if not self.telemetry.is_open:
            self.telemetry_status.emit(False)
            return
        for line in lines:
            if line == b"PONG":
                self.pong_received.emit()
            else:
                self.telemetry_line.emit(line)

    def _poll_logs(self):
        if not self.logs.is_open:
            return
        lines = self.logs.poll_lines()
        if not self.logs.is_open:
            self.log_status.emit(False)
            return
        for line in lines:
            try:
                self.log_line.emit(line.decode(errors="ignore"))
            except Exception:
                pass

    def send_ping(self):
        if self.telemetry.send(b"PING\n"):
            self.ping_sent.emit()

    # ── Serial ───────────────────────────────────────────────────────
    def open_serial(self, port: str, baud: int = None):
        ok = self.serial.open(port, baud or config.SERIAL_BAUD)
        msg = f"Serial aberta: {port}" if ok else f"Serial indisponível em {port}"
        self.serial_status.emit(ok, msg)

    def send_control(self, cmd) -> bool:
        line = f"{cmd.throttle},{cmd.aileron},{cmd.rudder},{cmd.elevator}\n"
        return self.serial.write_line(line)

    # ── Encerramento ─────────────────────────────────────────────────
    def shutdown(self):
        self.telemetry.close()
        self.logs.close()
        self.serial.close()