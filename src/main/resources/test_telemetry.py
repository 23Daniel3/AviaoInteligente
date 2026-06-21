"""
Testes do parser de telemetria — não dependem de PyQt5/pyvista, então
rodam em qualquer ambiente com `python -m unittest discover tests`.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import GpsFixState, PowerState
from telemetry import parse_line


class TestImuParsing(unittest.TestCase):
    def test_legacy_format_sem_prefixo(self):
        tag, data = parse_line(b"1.5,-2.3,180.0")
        self.assertEqual(tag, "IMU")
        self.assertEqual((data.roll, data.pitch, data.yaw), (1.5, -2.3, 180.0))

    def test_formato_novo_com_prefixo(self):
        tag, data = parse_line(b"IMU,10.0,20.0,30.0")
        self.assertEqual(tag, "IMU")
        self.assertEqual(data.roll, 10.0)

    def test_valores_nao_finitos_sao_rejeitados(self):
        self.assertIsNone(parse_line(b"IMU,nan,1,2"))
        self.assertIsNone(parse_line(b"IMU,inf,1,2"))


class TestBatteryParsing(unittest.TestCase):
    def test_bateria_normal(self):
        tag, data = parse_line(b"BAT,11.4")
        self.assertEqual(tag, "BAT")
        self.assertEqual(data.state, PowerState.NORMAL)

    def test_bateria_critica_3s(self):
        # 9.6V / 3 celulas = 3.2V/celula -> abaixo do limite critico (3.30)
        _, data = parse_line(b"BAT,9.6")
        self.assertEqual(data.state, PowerState.CRITICA)

    def test_percentual_cresce_com_tensao(self):
        _, baixa = parse_line(b"BAT,10.5")
        _, alta = parse_line(b"BAT,12.6")
        self.assertLess(baixa.percent, alta.percent)


class TestGpsParsing(unittest.TestCase):
    def test_fix_valido(self):
        tag, data = parse_line(b"GPS,1,-26.919400,-49.066100,420.5,35.2,9,20062026,153045")
        self.assertEqual(tag, "GPS")
        self.assertEqual(data.fix, GpsFixState.FIX_VALIDO)
        self.assertEqual(data.date_str, "20/06/2026")
        self.assertEqual(data.time_str, "15:30:45")

    def test_sem_fix(self):
        _, data = parse_line(b"GPS,0,0,0,0,0,0,00000000,000000")
        self.assertEqual(data.fix, GpsFixState.SEM_FIX)


class TestLinhasMalformadas(unittest.TestCase):
    def test_nao_levanta_excecao(self):
        for linha in (b"", b"lixo total", b"IMU,abc,def,ghi", b"BAT", b"GPS,1,2,3", b"1.0,2.0"):
            self.assertIsNone(parse_line(linha))


if __name__ == "__main__":
    unittest.main()