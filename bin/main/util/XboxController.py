import pygame
import time

class XboxController:
    def __init__(self, port=0):
        pygame.init()
        pygame.joystick.init()
        self.port = port
        self.joystick = None
        self.connect_controller()

    def connect_controller(self):
        while pygame.joystick.get_count() == 0:
            print("[Aviso] Nenhum controle encontrado. Conecte um controle.")
            time.sleep(2)
            pygame.joystick.quit()
            pygame.joystick.init()
        
        self.joystick = pygame.joystick.Joystick(self.port)
        self.joystick.init()
        print("Controle conectado!")

    def refresh(self):
        """Atualiza os eventos do pygame para capturar os estados mais recentes."""
        pygame.event.pump()
    
    def get_buttons(self):
        self.refresh()
        return {f'button_{i}': self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())}
    
    def button(self, button_index):
        self.refresh()
        return self.joystick.get_button(button_index) == 1
    
    def get_axes(self):
        self.refresh()
        return {f'ax{i}': round(self.joystick.get_axis(i), 2) for i in range(self.joystick.get_numaxes())}
    
    def get_hats(self):
        self.refresh()
        return self.joystick.get_hat(0)
    
    def get_all_inputs(self):
        return {
            "buttons": self.get_buttons(),
            "axes": self.get_axes(),
            "hats": self.get_hats()
        }

    def getA(self):
        return self.button(0)
    
    def getB(self):
        return self.button(1)
    
    def getX(self):
        return self.button(2)
    
    def getY(self):
        return self.button(3)
    
    def getLeftBumper(self):
        return self.button(4)
    
    def getRightBumper(self):
        return self.button(5)
    
    def getBack(self):
        return self.button(6)
    
    def getStart(self):
        return self.button(7)
    
    def getLeftStick(self):
        return self.button(8)
    
    def getRightStick(self):
        return self.button(9)
    
    def getPOVUp(self):
        return self.get_hats()[1] == 1
    
    def getPOVDown(self):
        return self.get_hats()[1] == -1
    
    def getPOVLeft(self):
        return self.get_hats()[0] == -1
    
    def getPOVRight(self):
        return self.get_hats()[0] == 1
    
    def getLeftX(self):
        self.refresh()
        return round(self.joystick.get_axis(0), 2)
    
    def getLeftY(self):
        self.refresh()
        return round(-self.joystick.get_axis(1), 2)
    
    def getRightX(self):
        self.refresh()
        return round(self.joystick.get_axis(2), 2)
    
    def getRightY(self):
        self.refresh()
        return round(-self.joystick.get_axis(3), 2)
    
    def close(self):
        if self.joystick:
            self.joystick.quit()
        pygame.quit()

