"""Card reutilizável: título + valor grande + ponto de status colorido +
subtítulo opcional. É o bloco de construção visual de toda a dashboard —
qualquer painel novo deve compor StatusCards em vez de inventar outro
estilo de exibição de número."""
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from theme import Colors


class StatusCard(QFrame):
    def __init__(self, title: str, value: str = "--", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(4)

        header = QHBoxLayout()
        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("cardTitle")
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {Colors.GRAY}; font-size: 13px;")
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.dot)
        layout.addLayout(header)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        layout.addWidget(self.value_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("cardSubtitle")
        self.subtitle_label.setVisible(bool(subtitle))
        layout.addWidget(self.subtitle_label)

    def set_value(self, value: str, color: str = None):
        self.value_label.setText(value)
        self.value_label.setStyleSheet(f"color: {color};" if color else "")

    def set_subtitle(self, text: str):
        self.subtitle_label.setText(text)
        self.subtitle_label.setVisible(bool(text))

    def set_state_color(self, color: str):
        self.dot.setStyleSheet(f"color: {color}; font-size: 13px;")