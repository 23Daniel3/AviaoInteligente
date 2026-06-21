"""
Parser do protocolo de telemetria. Uma linha de texto = uma mensagem.
Especificação completa em TELEMETRY_PROTOCOL.md.

Formatos aceitos:
  IMU,<roll>,<pitch>,<yaw>                                          (graus)
  BAT,<voltage>                                                     (volts, pack completo)
  GPS,<valid 0|1>,<lat>,<lon>,<alt_m>,<speed_kmh>,<sats>,<ddmmyyyy>,<hhmmss>
  roll,pitch,yaw                                                    (formato legado, sem prefixo)

parse_line nunca levanta exceção: entrada malformada vira None.
"""
import math

import config
from models import BatteryData, GpsData, GpsFixState, ImuData, PowerState


def _is_finite(x) -> bool:
    try:
        return math.isfinite(x)
    except Exception:
        return False


# Curva de descarga típica de uma célula LiPo (V/célula -> % de carga).
# Não é linear: a tensão cai rápido no início e no fim, e fica
# relativamente estável no meio — por isso a tabela em vez de uma reta.
_LIPO_CURVE_V_PCT = [
    (4.20, 100), (4.10, 95), (4.00, 85), (3.90, 75), (3.80, 65),
    (3.70, 50), (3.62, 40), (3.55, 25), (3.45, 15), (3.30, 5),
    (3.00, 0),
]


def estimate_battery_percent(voltage: float) -> float:
    """Estima a % de carga a partir da tensão total do pack."""
    if voltage <= 0 or config.BATTERY_CELLS <= 0:
        return 0.0
    v_cell = voltage / config.BATTERY_CELLS
    curve = _LIPO_CURVE_V_PCT
    if v_cell >= curve[0][0]:
        return 100.0
    if v_cell <= curve[-1][0]:
        return 0.0
    for (v_hi, p_hi), (v_lo, p_lo) in zip(curve, curve[1:]):
        if v_lo <= v_cell <= v_hi:
            frac = (v_cell - v_lo) / (v_hi - v_lo)
            return round(p_lo + frac * (p_hi - p_lo), 1)
    return 0.0


def classify_power_state(voltage: float) -> PowerState:
    if voltage <= 0 or config.BATTERY_CELLS <= 0:
        return PowerState.DESCONHECIDO
    v_cell = voltage / config.BATTERY_CELLS
    if v_cell <= config.BATTERY_CRITICAL_V_CELL:
        return PowerState.CRITICA
    if v_cell <= config.BATTERY_LOW_V_CELL:
        return PowerState.BAIXA
    return PowerState.NORMAL


def _parse_legacy_imu(parts):
    try:
        roll, pitch, yaw = map(float, parts)
    except ValueError:
        return None
    if not (_is_finite(roll) and _is_finite(pitch) and _is_finite(yaw)):
        return None
    return "IMU", ImuData(roll=roll, pitch=pitch, yaw=yaw)


def _parse_imu(fields):
    if len(fields) != 3:
        return None
    try:
        roll, pitch, yaw = map(float, fields)
    except ValueError:
        return None
    if not (_is_finite(roll) and _is_finite(pitch) and _is_finite(yaw)):
        return None
    return "IMU", ImuData(roll=roll, pitch=pitch, yaw=yaw)


def _parse_bat(fields):
    if len(fields) < 1:
        return None
    try:
        voltage = float(fields[0])
    except ValueError:
        return None
    if not _is_finite(voltage):
        return None
    return "BAT", BatteryData(
        voltage=voltage,
        percent=estimate_battery_percent(voltage),
        state=classify_power_state(voltage),
    )


def _parse_gps(fields):
    if len(fields) < 8:
        return None
    try:
        valid = fields[0] == "1"
        lat, lon, alt, speed = (float(x) for x in fields[1:5])
        sats = int(float(fields[5]))
    except (ValueError, IndexError):
        return None

    date_raw, time_raw = fields[6], fields[7]
    date_str = (
        f"{date_raw[0:2]}/{date_raw[2:4]}/{date_raw[4:8]}"
        if len(date_raw) == 8 else "--/--/----"
    )
    time_str = (
        f"{time_raw[0:2]}:{time_raw[2:4]}:{time_raw[4:6]}"
        if len(time_raw) == 6 else "--:--:--"
    )

    fix = (
        GpsFixState.FIX_VALIDO
        if valid and _is_finite(lat) and _is_finite(lon) and (lat, lon) != (0.0, 0.0)
        else GpsFixState.SEM_FIX
    )
    return "GPS", GpsData(
        lat=lat, lon=lon, altitude=alt, speed_kmh=speed,
        satellites=sats, fix=fix, date_str=date_str, time_str=time_str,
    )


def parse_line(raw):
    """raw: bytes ou str. Retorna ('IMU'|'BAT'|'GPS', dataclass) ou None."""
    if isinstance(raw, bytes):
        try:
            line = raw.decode(errors="ignore").strip()
        except Exception:
            return None
    else:
        line = str(raw).strip()

    if not line:
        return None

    parts = line.split(",")

    if parts[0] not in ("IMU", "BAT", "GPS"):
        # formato legado: "roll,pitch,yaw" sem prefixo
        if len(parts) == 3:
            return _parse_legacy_imu(parts)
        return None

    tag, fields = parts[0], parts[1:]
    if tag == "IMU":
        return _parse_imu(fields)
    if tag == "BAT":
        return _parse_bat(fields)
    if tag == "GPS":
        return _parse_gps(fields)
    return None