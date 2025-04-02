import websocket
import pygame
from util.XboxController import XboxController  # Certifique-se de que o arquivo XboxController.py está na pasta "util"

class XboxWebSocketClient:
    def __init__(self, esp_ip="192.168.4.1"):
        self.esp_ip = esp_ip
        self.ws = None
        self.controller = XboxController()

    def conectar(self):
        try:
            self.ws = websocket.create_connection(f"ws://{self.esp_ip}:81")
        except Exception as e:
            print(f"Erro ao conectar ao WebSocket: {e}")
            self.ws = None

    def enviar_comando(self, comando):
        if self.ws:
            try:
                self.ws.send(comando)
            except Exception as e:
                print(f"Erro ao enviar comando: {e}")
        else:
            print("WebSocket não conectado. Tentando reconectar...")
            self.conectar()
            if self.ws:
                self.enviar_comando(comando)

    def verificar_botoes(self):
        if self.controller.getA():  # Botão A pressionado
            print("Botão A pressionado - Acendendo LED")
            self.enviar_comando("acender")
        
        if self.controller.getB():  # Botão B pressionado
            print("Botão B pressionado - Apagando LED")
            self.enviar_comando("apagar")

    def iniciar_loop(self):
        try:
            while True:
                self.verificar_botoes()
                pygame.time.wait(100)  # Pequeno delay para não sobrecarregar a CPU
        except KeyboardInterrupt:
            print("Fechando o programa.")
        finally:
            self.fechar()

    def fechar(self):
        if self.ws:
            self.ws.close()
        self.controller.close()

# Exemplo de uso:
if __name__ == "__main__":
    client = XboxWebSocketClient()
    client.conectar()
    client.iniciar_loop()
