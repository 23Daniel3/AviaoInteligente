"""Faixa de alerta grande no topo da dashboard. Fica com altura zero
(invisível) quando não há problema algum. Suporta múltiplas fontes de
alerta simultâneas via chave (ex.: "bateria", "gps", "link") — cada
módulo cuida da sua própria chave, sem pisar no alerta dos outros.
Alertas de nível "critico" piscam para chamar atenção de verdade."""
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QLabel

from theme import Colors


class AlertBanner(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self._messages = {}  # chave -> (texto, nivel)
        self._current_level = None
        self._blink_on = True

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_blink)
        self._blink_timer.start(500)

        self._apply(None, None)

    def set_alert(self, key: str, message: str = None, level: str = "critico"):
        """message=None remove o alerta dessa chave."""
        if message is None:
            self._messages.pop(key, None)
        else:
            self._messages[key] = (message, level)
        self._refresh()

    def _refresh(self):
        if not self._messages:
            self._apply(None, None)
            return
        criticos = [m for m, lvl in self._messages.values() if lvl == "critico"]
        atencao = [m for m, lvl in self._messages.values() if lvl == "atencao"]
        if criticos:
            self._apply(" • ".join(criticos), "critico")
        else:
            self._apply(" • ".join(atencao), "atencao")

    def _toggle_blink(self):
        if self._current_level != "critico":
            return
        self._blink_on = not self._blink_on
        self.setStyleSheet(self._style_for("critico", dim=not self._blink_on))

    def _apply(self, text, level):
        self._current_level = level
        if text is None:
            self.setText("")
            self.setFixedHeight(0)
            return
        self.setText(f"⚠  {text}")
        self.setStyleSheet(self._style_for(level))
        self.setFixedHeight(40)

    @staticmethod
    def _style_for(level, dim: bool = False) -> str:
        if level == "critico":
            bg = "#7a1f1c" if dim else Colors.RED
            fg = "#ffffff"
        else:
            bg = Colors.YELLOW
            fg = "#1a1a1a"
        return (
            f"background: {bg}; color: {fg}; font-weight: 700; "
            f"font-size: 14px; border-radius: 8px; padding: 8px;"
        )