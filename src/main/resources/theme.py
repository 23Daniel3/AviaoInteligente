"""
Paleta e folha de estilos (QSS) da dashboard.

Direção visual: estação de controle de voo profissional — fundo escuro
para reduzir fadiga visual em uso prolongado, alto contraste para os
números que importam, e três cores de estado universais (verde/amarelo/
vermelho) usadas de forma consistente em toda a aplicação.
"""


class Colors:
    BG = "#0b0f17"
    SURFACE = "#141a24"
    SURFACE_ALT = "#1b2330"
    BORDER = "#2a3242"
    TEXT = "#e6edf3"
    TEXT_MUTED = "#8b96a5"
    ACCENT = "#3fb6ff"

    GREEN = "#3fb950"
    YELLOW = "#d4a72c"
    RED = "#f85149"
    GRAY = "#6e7681"


def state_color(level: str) -> str:
    """level: 'normal' | 'atencao' | 'critico' | 'offline'."""
    return {
        "normal": Colors.GREEN,
        "atencao": Colors.YELLOW,
        "critico": Colors.RED,
        "offline": Colors.GRAY,
    }.get(level, Colors.GRAY)


def build_qss() -> str:
    c = Colors
    return f"""
    QMainWindow, QWidget {{
        background-color: {c.BG};
        color: {c.TEXT};
        font-family: 'Segoe UI', 'Inter', sans-serif;
        font-size: 13px;
    }}
    QTabWidget::pane {{
        border: 1px solid {c.BORDER};
        background: {c.BG};
        top: -1px;
    }}
    QTabBar::tab {{
        background: {c.SURFACE};
        color: {c.TEXT_MUTED};
        padding: 8px 20px;
        border: 1px solid {c.BORDER};
        border-bottom: none;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {c.BG};
        color: {c.TEXT};
        border-bottom: 2px solid {c.ACCENT};
    }}
    QLabel#cardTitle {{
        color: {c.TEXT_MUTED};
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1px;
    }}
    QLabel#cardValue {{
        font-size: 21px;
        font-weight: 700;
        color: {c.TEXT};
    }}
    QLabel#cardSubtitle {{
        color: {c.TEXT_MUTED};
        font-size: 11px;
    }}
    QFrame#card {{
        background: {c.SURFACE};
        border: 1px solid {c.BORDER};
        border-radius: 10px;
    }}
    QGroupBox {{
        border: 1px solid {c.BORDER};
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 12px;
        font-weight: 600;
        color: {c.TEXT_MUTED};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }}
    QPushButton {{
        background: {c.SURFACE_ALT};
        color: {c.TEXT};
        border: 1px solid {c.BORDER};
        border-radius: 6px;
        padding: 6px 14px;
    }}
    QPushButton:hover {{
        background: {c.BORDER};
        border-color: {c.ACCENT};
    }}
    QPushButton:pressed {{
        background: {c.ACCENT};
        color: {c.BG};
    }}
    QLineEdit, QDoubleSpinBox {{
        background: {c.SURFACE_ALT};
        border: 1px solid {c.BORDER};
        border-radius: 6px;
        padding: 4px 8px;
        color: {c.TEXT};
        selection-background-color: {c.ACCENT};
    }}
    QTextEdit {{
        background: {c.SURFACE};
        border: 1px solid {c.BORDER};
        border-radius: 8px;
        font-family: Consolas, 'Courier New', monospace;
        font-size: 12px;
        padding: 6px;
    }}
    QProgressBar {{
        background: {c.SURFACE_ALT};
        border: 1px solid {c.BORDER};
        border-radius: 6px;
        text-align: center;
        color: {c.TEXT};
        height: 18px;
    }}
    QProgressBar::chunk {{
        border-radius: 5px;
    }}
    QScrollBar:vertical {{
        background: {c.BG};
        width: 10px;
    }}
    QScrollBar::handle:vertical {{
        background: {c.BORDER};
        border-radius: 5px;
        min-height: 24px;
    }}
    """