import websocket
import pygame
from util.XboxController import XboxController  # Certifique-se de que o arquivo XboxController.py está na pasta "útil"

esp_ip = "192.168.4.1"  # IP do ESP32 na rede criada

# Função para enviar comandos ao ESP32
def enviar_comando(comando):
    ws = websocket.create_connection(f"ws://{esp_ip}:81")
    ws.send(comando)
    ws.close()

# Inicialize o controle Xbox
controller = XboxController()

try:
    while True:
        # Verificar os botões pressionados
        if controller.getA():  # Botão A pressionado
            print("Botão A pressionado - Acendendo LED")
            enviar_comando("acender")
        
        if controller.getB():  # Botão B pressionado
            print("Botão B pressionado - Apagando LED")
            enviar_comando("apagar")
        
        pygame.time.wait(100)  # Pequeno delay para não sobrecarregar a CPU

except KeyboardInterrupt:
    print("Fechando o programa.")
finally:
    controller.close()  # Fechar o controlador quando terminar
