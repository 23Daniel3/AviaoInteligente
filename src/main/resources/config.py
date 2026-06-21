"""
Configurações centrais da Dashboard de Telemetria.

Tudo que normalmente muda de uma máquina/aeronave para outra fica aqui —
o resto do código nunca deve ter números "mágicos" espalhados.
"""
from pathlib import Path

# ── Conexão ──────────────────────────────────────────────────────────
SERIAL_PORT = "COM4"          # porta USB do transmissor (ground station)
SERIAL_BAUD = 115200

ESP32_DEFAULT_IP = "192.168.4.1"   # IP do ESP32-S3 embarcado (AP do avião)
TELEMETRY_PORT = 8080              # IMU + bateria + GPS + PONG
LOG_PORT = 9090                    # logs de texto livre do firmware

# ── Modelo 3D ────────────────────────────────────────────────────────
# Ajuste para o caminho real do seu .obj
MODELO_PATH = Path(
    "C:/Users/danie/Desktop/Programacao/Aviao_Inteligente/src/main/resources/modelo.obj"
)

# ── Temporização (ms, exceto onde indicado) ───────────────────────────
RECONNECT_INTERVAL_MS = 3000   # tentativa de reconexão dos sockets TCP
GYRO_POLL_MS = 2                # leitura do socket de telemetria
LOG_POLL_MS = 200               # leitura do socket de logs
CONTROL_SEND_MS = 20            # 50 Hz — igual ao loop do transmissor
QUALITY_UPDATE_MS = 1000        # recálculo de pacotes/s, qualidade, latência
PING_INTERVAL_MS = 2000         # intervalo do PING para medir latência

# ── Qualidade de link ──────────────────────────────────────────────────
EXPECTED_PACKET_RATE_HZ = 50    # taxa esperada de pacotes IMU/seg (BNO080 a 50Hz)
CONNECTION_TIMEOUT_S = 1.5      # sem pacote por esse tempo => "offline"
LATENCY_GOOD_MS = 50
LATENCY_WARN_MS = 200

# ── Bateria (LiPo) ──────────────────────────────────────────────────────
# Ajuste BATTERY_CELLS para o pack realmente usado na aeronave (2S/3S/4S...).
# A % de carga é estimada por uma curva de descarga típica (ver core/telemetry.py).
BATTERY_CELLS = 3
BATTERY_LOW_V_CELL = 3.55       # abaixo disso => estado "baixa"
BATTERY_CRITICAL_V_CELL = 3.30  # abaixo disso => estado "crítica"

# ── Joystick → PWM ──────────────────────────────────────────────────────
PWM_DEADZONE = 0.08
THROTTLE_PWM_MIN, THROTTLE_PWM_MAX = 1000, 2000
SERVO_PWM_MIN, SERVO_PWM_MAX = 500, 2500

# ── GPS ──────────────────────────────────────────────────────────────────
GPS_MIN_SATS_GOOD = 6   # >= disso: indicador verde
GPS_MIN_SATS_OK = 3     # >= disso: indicador amarelo; abaixo: vermelho