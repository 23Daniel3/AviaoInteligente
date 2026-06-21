"""
Converte eixos do controle (-1.0 .. 1.0) em pulsos PWM (microssegundos)
e produz um ControlCommand pronto para ser enviado pela serial.

Isolado em módulo próprio para poder trocar o dispositivo de entrada
(outro controle, um joystick de simulador, um script de teste) sem
tocar na lógica de comunicação nem na UI.
"""
import config
from models import ControlCommand


def _apply_deadzone(axis: float) -> float:
    return 0.0 if abs(axis) < config.PWM_DEADZONE else axis


def throttle_to_pwm(axis: float) -> int:
    """Left trigger -> THROTTLE_PWM_MIN..MAX (o ESC não aceita fora disso)."""
    axis = max(-1.0, min(1.0, _apply_deadzone(axis)))
    mid = (config.THROTTLE_PWM_MIN + config.THROTTLE_PWM_MAX) / 2
    half_range = (config.THROTTLE_PWM_MAX - config.THROTTLE_PWM_MIN) / 2
    return int(mid + axis * half_range)


def servo_to_pwm(axis: float) -> int:
    """Joystick -> SERVO_PWM_MIN..MAX (curso total dos servos)."""
    axis = max(-1.0, min(1.0, _apply_deadzone(axis)))
    mid = (config.SERVO_PWM_MIN + config.SERVO_PWM_MAX) / 2
    half_range = (config.SERVO_PWM_MAX - config.SERVO_PWM_MIN) / 2
    return int(mid + axis * half_range)


class ControllerInput:
    """Encapsula o XboxController e produz um ControlCommand a cada chamada.

    Mantém a mesma interface que XboxController já expõe no projeto original
    (getLeftTrigger, getLeftX, getRightX, getRightY) — basta reutilizar o
    util/XboxController.py existente.
    """

    def __init__(self, controller=None):
        self.controller = controller

    @property
    def is_connected(self) -> bool:
        return self.controller is not None

    def read_command(self) -> ControlCommand:
        if not self.controller:
            return ControlCommand()
        try:
            throttle = throttle_to_pwm(-self.controller.getLeftTrigger())
            aileron = servo_to_pwm(self.controller.getLeftX())
            rudder = servo_to_pwm(self.controller.getRightX())
            elevator = servo_to_pwm(self.controller.getRightY())
            return ControlCommand(throttle, aileron, rudder, elevator)
        except Exception:
            # controle desconectou no meio do uso — não derruba a aplicação
            self.controller = None
            return ControlCommand()