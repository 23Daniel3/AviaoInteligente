import sys
from PyQt5.QtWidgets import QApplication
from dashboard import Dashboard  # Certifique-se de que o nome do arquivo da dashboard é "dashboard.py"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    modelo_path = "C:/Users/danie/Desktop/Programacao/Avião Inteligente/src/main/resources/modelo.obj"
    window = Dashboard(modelo_path)
    window.show()
    sys.exit(app.exec_())
