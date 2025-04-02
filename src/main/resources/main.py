import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from dashboard import Dashboard
from util.XboxController import XboxController

if __name__ == "__main__":
    app = QApplication(sys.argv)
    modelo_path = "C:/Users/danie/Desktop/Programacao/Avião Inteligente/src/main/resources/modelo.obj"
    window = Dashboard(modelo_path)
    window.show()

    controller = XboxController()

    # Criando um timer para atualizar a rotação continuamente sem bloquear a interface
    def update_rotation():
        pitch = -controller.getRightY()*90  # Ajuste conforme necessário
        roll = -controller.getRightX()*90
        window.set_rotation(0, pitch, roll)

    timer = QTimer()
    timer.timeout.connect(update_rotation)
    timer.start(50)

    sys.exit(app.exec_())
