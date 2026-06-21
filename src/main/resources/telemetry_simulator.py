"""
Simulador de telemetria — permite testar a dashboard inteira (conexão,
qualidade de sinal, IMU, bateria, GPS, alertas) sem precisar do ESP32
nem do avião por perto.

Abre dois servidores TCP, no mesmo protocolo descrito em
TELEMETRY_PROTOCOL.md:
  - porta 8080: IMU (50Hz), bateria (~1Hz), GPS (~1Hz), responde PONG a PING
  - porta 9090: linhas de log fake a cada poucos segundos

Uso:
    python tools/telemetry_simulator.py
Depois, na dashboard, aplique o IP 127.0.0.1 em "Configuração de Link".
"""
import math
import random
import socket
import threading
import time

TELEMETRY_PORT = 8080
LOG_PORT = 9090

# Ponto de partida fictício (Blumenau/SC) só para a trajetória ter cara de voo real
LAT0, LON0 = -26.9194, -49.0661


def _telemetry_session(conn):
    t0 = time.time()
    last_slow_tick = 0
    conn.setblocking(False)
    try:
        while True:
            t = time.time() - t0

            roll = 20 * math.sin(t * 0.7)
            pitch = 10 * math.sin(t * 0.5 + 1)
            yaw = (t * 15) % 360 - 180
            conn.send(f"IMU,{roll:.2f},{pitch:.2f},{yaw:.2f}\n".encode())

            if int(t) != last_slow_tick:  # ~1x/segundo
                last_slow_tick = int(t)

                voltage = max(9.0, 12.6 - (t / 900))  # descarrega bem devagar
                conn.send(f"BAT,{voltage:.2f}\n".encode())

                lat = LAT0 + 0.0008 * math.sin(t * 0.04)
                lon = LON0 + 0.0008 * math.cos(t * 0.04)
                now = time.gmtime()
                date_str = time.strftime("%d%m%Y", now)
                time_str = time.strftime("%H%M%S", now)
                conn.send(
                    f"GPS,1,{lat:.6f},{lon:.6f},420.0,35.0,9,{date_str},{time_str}\n".encode()
                )

            try:
                data = conn.recv(64)
                if not data:
                    break
                if b"PING" in data:
                    conn.send(b"PONG\n")
            except BlockingIOError:
                pass

            time.sleep(0.02)  # 50 Hz, igual ao firmware real
    except (BrokenPipeError, ConnectionResetError, OSError):
        pass
    finally:
        conn.close()


def telemetry_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", TELEMETRY_PORT))
    srv.listen(1)
    print(f"[SIM] Telemetria escutando na porta {TELEMETRY_PORT}...")
    while True:
        conn, addr = srv.accept()
        print(f"[SIM] Dashboard conectada (telemetria): {addr}")
        _telemetry_session(conn)
        print("[SIM] Dashboard desconectada (telemetria)")


def log_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", LOG_PORT))
    srv.listen(1)
    print(f"[SIM] Log escutando na porta {LOG_PORT}...")
    msgs = ["Sistema operacional", "Loop estável", "Sem erros reportados", "BNO080 OK"]
    while True:
        conn, addr = srv.accept()
        print(f"[SIM] Dashboard conectada (log): {addr}")
        try:
            while True:
                conn.send((random.choice(msgs) + "\n").encode())
                time.sleep(3)
        except (BrokenPipeError, ConnectionResetError, OSError):
            print("[SIM] Dashboard desconectada (log)")
        finally:
            conn.close()


if __name__ == "__main__":
    threading.Thread(target=telemetry_server, daemon=True).start()
    threading.Thread(target=log_server, daemon=True).start()
    print("Simulador rodando. Ctrl+C para sair.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrado.")