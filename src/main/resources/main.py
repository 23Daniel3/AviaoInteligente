"""Ponto de entrada. Mantém o arquivo enxuto de propósito — toda a
lógica de montagem da janela vive em ui/main_window.py."""
import sys

from PyQt5.QtWidgets import QApplication, QMessageBox

from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
    except Exception as e:
        QMessageBox.critical(None, "Erro ao iniciar a dashboard", str(e))
        sys.exit(1)
        return
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()