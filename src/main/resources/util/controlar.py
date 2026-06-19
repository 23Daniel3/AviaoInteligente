import time
import serial
from XboxController import XboxController

def map_lefty_to_pwm(left_y: float) -> int:
    # Deadzone ao redor do centro
    if abs(left_y) < 0.08:
        left_y = 0.0

    left_y = max(-1.0, min(1.0, left_y))

    return int(1500 + left_y * 500)

controller = XboxController()
ser = serial.Serial("COM4", 115200, timeout=0.05)  # troque a porta
time.sleep(2)

last_pwm = None

while True:
    ly = -controller.getLeftTrigger()
    pwm = map_lefty_to_pwm(ly)
    if pwm != last_pwm:
        ser.write(f"{pwm}\n".encode())
        ser.flush()
        print(f"LeftY={ly:.2f} -> {pwm}")
        last_pwm = pwm

    time.sleep(0.02)