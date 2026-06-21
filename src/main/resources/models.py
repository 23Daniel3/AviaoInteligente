"""
Modelos de dados imutáveis-o-suficiente que trafegam entre comunicação,
telemetria e interface. Adicionar um novo sensor normalmente começa aqui:
crie a dataclass, depois ensine core/telemetry.py a parseá-la.
"""
from dataclasses import dataclass, field
from enum import Enum
import time


class PowerState(Enum):
    DESCONHECIDO = "desconhecido"
    NORMAL = "normal"
    BAIXA = "baixa"
    CRITICA = "critica"


class GpsFixState(Enum):
    SEM_DADOS = "sem_dados"   # nenhuma mensagem GPS recebida ainda
    SEM_FIX = "sem_fix"       # mensagem recebida, mas sem posição válida
    FIX_VALIDO = "fix_valido"


@dataclass
class ImuData:
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class BatteryData:
    voltage: float = 0.0
    percent: float = 0.0
    state: PowerState = PowerState.DESCONHECIDO
    timestamp: float = field(default_factory=time.time)


@dataclass
class GpsData:
    lat: float = 0.0
    lon: float = 0.0
    altitude: float = 0.0
    speed_kmh: float = 0.0
    satellites: int = 0
    fix: GpsFixState = GpsFixState.SEM_DADOS
    date_str: str = "--/--/----"
    time_str: str = "--:--:--"
    timestamp: float = field(default_factory=time.time)


@dataclass
class ControlCommand:
    throttle: int = 1000
    aileron: int = 1500
    rudder: int = 1500
    elevator: int = 1500


@dataclass
class LinkQuality:
    connected: bool = False
    packets_per_second: int = 0
    quality_percent: int = 0
    latency_ms: float = None