"""
comunicacao.py — Módulo de Comunicação Serial
Responsabilidade única: abrir a porta serial, ler JSONs linha a linha,
decodificar e disponibilizar os dados para a dashboard.
Também faz logging automático em CSV e envia comandos de volta ao Arduino.
"""

import serial
import serial.tools.list_ports
import threading
import json
import csv
import time
import logging
from datetime import datetime
from pathlib import Path
from collections import deque
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SerialCommunicator:
    """
    Lê dados JSON de uma porta serial (Arduino/ESP32) em uma thread separada.

    Uso básico:
        comm = SerialCommunicator(port="COM3", baud=115200)
        comm.on_telemetry(lambda data: print(data))
        comm.start()
        ...
        comm.stop()

    Para adicionar novos tipos de mensagem, basta registrar um handler:
        comm.on_message_type("meu_tipo", meu_callback)
    """

    LOG_DIR = Path("logs")
    MAX_HISTORY = 500   # Pontos mantidos em memória por campo

    def __init__(self, port: Optional[str] = None, baud: int = 115200):
        self.port  = port or self._auto_detect_port()
        self.baud  = baud
        self._ser: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

        # Último pacote de telemetria recebido (acesso thread-safe com lock)
        self._lock    = threading.Lock()
        self._latest: dict = {}

        # Histórico por campo: {"roll": deque([...]), "pitch": deque([...]), ...}
        self._history: dict[str, deque] = {}
        self._timestamps: deque = deque(maxlen=self.MAX_HISTORY)

        # Callbacks por tipo de mensagem JSON
        self._handlers: dict[str, list[Callable]] = {}

        # CSV logging
        self.LOG_DIR.mkdir(exist_ok=True)
        session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._csv_path = self.LOG_DIR / f"telemetria_{session_ts}.csv"
        self._csv_file = None
        self._csv_writer = None
        self._csv_headers_written = False

        # Fila de comandos para envio
        self._cmd_queue: deque = deque(maxlen=10)

        # Estatísticas
        self.packets_received = 0
        self.packets_error    = 0
        self.connected        = False

    # -----------------------------------------------------------------------
    # API Pública
    # -----------------------------------------------------------------------

    def start(self):
        """Inicia a thread de leitura serial."""
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True, name="SerialReader")
        self._thread.start()
        logger.info(f"Comunicação iniciada em {self.port} @ {self.baud} baud")

    def stop(self):
        """Para a thread e fecha recursos."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._ser and self._ser.is_open:
            self._ser.close()
        if self._csv_file:
            self._csv_file.close()
        logger.info("Comunicação encerrada")

    def on_telemetry(self, callback: Callable):
        """Registra callback chamado para cada pacote de telemetria recebido."""
        self.on_message_type("telemetry", callback)

    def on_message_type(self, msg_type: str, callback: Callable):
        """Registra callback para um tipo específico de mensagem JSON."""
        self._handlers.setdefault(msg_type, []).append(callback)

    def get_latest(self) -> dict:
        """Retorna o último pacote de telemetria recebido (thread-safe)."""
        with self._lock:
            return dict(self._latest)

    def get_history(self, field: str) -> list:
        """Retorna o histórico de um campo específico."""
        with self._lock:
            return list(self._history.get(field, []))

    def get_timestamps(self) -> list:
        """Retorna a lista de timestamps correspondente ao histórico."""
        with self._lock:
            return list(self._timestamps)

    def send_command(self, payload: dict):
        """
        Enfileira um comando para envio ao Arduino.
        O payload será serializado como JSON + newline.

        Exemplo:
            comm.send_command({"throttle": 0.5, "aileron": 0.1})
        """
        self._cmd_queue.append(payload)

    @staticmethod
    def list_ports() -> list[str]:
        """Lista todas as portas seriais disponíveis."""
        return [p.device for p in serial.tools.list_ports.comports()]

    # -----------------------------------------------------------------------
    # Internos
    # -----------------------------------------------------------------------

    def _auto_detect_port(self) -> str:
        """Tenta detectar automaticamente a porta do ESP32."""
        known_descriptions = ["CP2102", "CH340", "USB Serial", "UART", "ESP32"]
        for port in serial.tools.list_ports.comports():
            desc = (port.description or "") + (port.manufacturer or "")
            if any(k.lower() in desc.lower() for k in known_descriptions):
                logger.info(f"ESP32 detectado em {port.device}")
                return port.device
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports:
            logger.warning(f"ESP32 não detectado automaticamente. Usando {ports[0]}")
            return ports[0]
        raise RuntimeError("Nenhuma porta serial encontrada!")

    def _read_loop(self):
        """Loop principal de leitura (roda em thread separada)."""
        while self._running:
            try:
                self._ser = serial.Serial(self.port, self.baud, timeout=1)
                self.connected = True
                logger.info(f"Conectado a {self.port}")
                self._run_connected_loop()
            except serial.SerialException as e:
                self.connected = False
                logger.error(f"Erro serial: {e} — reconectando em 2s")
                time.sleep(2)
            except Exception as e:
                self.connected = False
                logger.exception(f"Erro inesperado na leitura serial: {e}")
                time.sleep(2)

    def _run_connected_loop(self):
        """Loop de leitura enquanto a porta está aberta."""
        buf = b""
        while self._running and self._ser.is_open:
            # Envia comandos pendentes
            while self._cmd_queue:
                cmd = self._cmd_queue.popleft()
                raw = (json.dumps(cmd) + "\n").encode()
                self._ser.write(raw)

            # Lê dados chegando
            try:
                chunk = self._ser.read(self._ser.in_waiting or 1)
            except serial.SerialException:
                break

            if chunk:
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    self._process_line(line.strip())

    def _process_line(self, raw: bytes):
        """Decodifica uma linha JSON e despacha para handlers registrados."""
        if not raw:
            return
        try:
            text = raw.decode("utf-8", errors="replace").strip()
            if not text.startswith("{"):
                return   # Ignora linhas de debug sem JSON

            data = json.loads(text)
            msg_type = data.get("type", "unknown")

            # Atualiza estado interno apenas para telemetria
            if msg_type == "telemetry":
                ts = time.time()
                with self._lock:
                    self._latest = data
                    self._timestamps.append(ts)
                    for key, val in data.items():
                        if key == "type":
                            continue
                        if key not in self._history:
                            self._history[key] = deque(maxlen=self.MAX_HISTORY)
                        self._history[key].append(val)

                self._log_to_csv(data, ts)
                self.packets_received += 1

            # Chama handlers registrados
            for cb in self._handlers.get(msg_type, []):
                try:
                    cb(data)
                except Exception as e:
                    logger.error(f"Erro no handler '{msg_type}': {e}")

            # Handler coringa "*" recebe tudo
            for cb in self._handlers.get("*", []):
                try:
                    cb(data)
                except Exception as e:
                    logger.error(f"Erro no handler '*': {e}")

        except json.JSONDecodeError:
            self.packets_error += 1
            logger.debug(f"JSON inválido: {raw[:80]}")
        except Exception as e:
            self.packets_error += 1
            logger.error(f"Erro processando linha: {e}")

    def _log_to_csv(self, data: dict, timestamp: float):
        """
        Salva o pacote em CSV. Cria o arquivo e os headers automaticamente.
        Se um campo novo aparecer, o CSV é recriado com os novos headers.
        """
        try:
            fields = {k: v for k, v in data.items() if k != "type"}
            fields["timestamp"] = timestamp
            fields["datetime"]  = datetime.fromtimestamp(timestamp).isoformat()

            if not self._csv_headers_written:
                self._csv_file = open(self._csv_path, "w", newline="", encoding="utf-8")
                self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=list(fields.keys()))
                self._csv_writer.writeheader()
                self._csv_headers_written = True

            self._csv_writer.writerow(fields)
            self._csv_file.flush()
        except Exception as e:
            logger.error(f"Erro ao salvar CSV: {e}")