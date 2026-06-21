"""
LinkMonitor: mede, de forma agnóstica ao transporte (TCP, serial, o que for),
a saúde de um canal de telemetria — taxa de pacotes, latência via PING/PONG,
e se está "conectado" (= recebendo dados há pouco tempo).

Não sabe nada sobre sockets; só recebe notificações (notify_packet,
notify_ping_sent, notify_pong) e calcula métricas quando pedido.
"""
import time

from models import LinkQuality


class LinkMonitor:
    def __init__(self, expected_rate_hz: int, timeout_s: float):
        self.expected_rate_hz = expected_rate_hz
        self.timeout_s = timeout_s
        self._pkt_count = 0
        self._last_packet_t = None
        self._latency_ms = None
        self._ping_sent_t = None

    def notify_packet(self):
        self._pkt_count += 1
        self._last_packet_t = time.time()

    def notify_ping_sent(self):
        self._ping_sent_t = time.time()

    def notify_pong(self):
        if self._ping_sent_t is not None:
            self._latency_ms = (time.time() - self._ping_sent_t) * 1000
            self._ping_sent_t = None

    @property
    def is_connected(self) -> bool:
        return (
            self._last_packet_t is not None
            and time.time() - self._last_packet_t < self.timeout_s
        )

    @property
    def seconds_since_last_packet(self):
        if self._last_packet_t is None:
            return None
        return time.time() - self._last_packet_t

    def sample_quality(self) -> LinkQuality:
        """Chamar 1x/segundo: devolve a métrica da janela e reseta o contador."""
        pps = self._pkt_count
        self._pkt_count = 0
        connected = self.is_connected
        quality_pct = 0
        if connected and self.expected_rate_hz:
            quality_pct = min(100, int(pps / self.expected_rate_hz * 100))
        return LinkQuality(
            connected=connected,
            packets_per_second=pps,
            quality_percent=quality_pct,
            latency_ms=self._latency_ms,
        )