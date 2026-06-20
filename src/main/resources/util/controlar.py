import time
import serial
from XboxController import XboxController

def map_motor_axis_to_pwm(axis: float) -> int:
    # Deadzone ao redor do centro — serve para triggers e joysticks
    if abs(axis) < 0.08:
        axis = 0.0

    axis = max(-1.0, min(1.0, axis))

    return int(1500 + axis * 500)

def map_servo_axis_to_pwm(axis: float) -> int:
    # Deadzone ao redor do centro — serve para triggers e joysticks
    if abs(axis) < 0.08:
        axis = 0.0

    axis = max(-1.0, min(1.0, axis))

    return int(1500 + axis * 1000)

controller = XboxController()
ser = serial.Serial("COM4", 115200, timeout=0.05)  # troque a porta
time.sleep(2)

last_packet = None

while True:
    # Throttle: Left Trigger (lógica original mantida)
    throttle = map_motor_axis_to_pwm(-controller.getLeftTrigger())

    # Aileron:   LeftX  (-1.0 → 1.0) → 1000–2000 us
    aileron  = map_servo_axis_to_pwm(controller.getLeftX())   # ajuste o nome ao seu XboxController

    # Leme:      RightX (-1.0 → 1.0) → 1000–2000 us
    rudder   = map_servo_axis_to_pwm(controller.getRightX())

    # Profundor: RightY (-1.0 → 1.0) → 1000–2000 us
    elevator = map_servo_axis_to_pwm(controller.getRightY())

    packet = (throttle, aileron, rudder, elevator)

    if packet != last_packet:
        # Formato CSV: "throttle,aileron,rudder,elevator\n"
        line = f"{throttle},{aileron},{rudder},{elevator}\n"
        ser.write(line.encode())
        ser.flush()
        print(f"thr={throttle} ail={aileron} rud={rudder} ele={elevator}")
        last_packet = packet

    time.sleep(0.02)