import pygame

class XboxController:
    
    DEADBAND = 0.1
    
    def __init__(self, port=0):
        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() == 0:
            raise Exception("Nenhum controle encontrado!")
        
        self.joystick = pygame.joystick.Joystick(port)
        self.joystick.init()
    
    def get_buttons(self):
        """Retorna um dicionário com o estado dos botões."""
        pygame.event.pump()
        return {f'button_{i}': self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())}
    
    def button(self, button_index):
        """Retorna True se o botão específico estiver pressionado, senão False."""
        pygame.event.pump()
        return self.joystick.get_button(button_index) == 1
    
    def get_axes(self):
        """Retorna um dicionário com os valores dos eixos analógicos."""
        pygame.event.pump()
        return {f'ax{i}': round(self.joystick.get_axis(i), 2) for i in range(self.joystick.get_numaxes())}
    
    def get_hats(self):
        """Retorna um dicionário com o estado dos direcionais digitais (D-Pad)."""
        pygame.event.pump()
        return self.joystick.get_hat(0)
    
    def get_all_inputs(self):
        """Retorna um dicionário com todos os dados do controle."""
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
        """Retorna o valor do eixo X do joystick esquerdo."""
        pygame.event.pump()
        return self.with_deadband(round(self.joystick.get_axis(0), 2))
    
    def getLeftY(self):
        """Retorna o valor do eixo Y do joystick esquerdo (invertido para alinhamento correto)."""
        pygame.event.pump()
        return self.with_deadband(round(-self.joystick.get_axis(1), 2))
    
    def getRightX(self):
        """Retorna o valor do eixo X do joystick direito."""
        pygame.event.pump()
        return self.with_deadband(round(self.joystick.get_axis(2), 2))
    
    def getRightY(self):
        """Retorna o valor do eixo Y do joystick direito."""
        pygame.event.pump()
        return self.with_deadband(-round(self.joystick.get_axis(3), 2))
    
    def getLeftTrigger(self):
        pygame.event.pump()
        raw_value = self.joystick.get_axis(4)
        return self.with_deadband(round((raw_value + 1) / 2, 2))
    
    def getRightTrigger(self):
        pygame.event.pump()
        raw_value = self.joystick.get_axis(5)
        return self.with_deadband(round((raw_value + 1) / 2, 2))
    
    def close(self):
        """Fecha a conexão com o controle."""
        self.joystick.quit()
        pygame.quit()
    
    def get_right_trigger_locked(self):
        """
        Retorna o valor do Right Trigger normalmente, mas se o LB for pressionado,
        ele mantém o valor do Right Trigger no momento da pressão do LB.
        """
        pygame.event.pump()
        right_trigger = self.getRightTrigger() 
        lb_pressed = self.getLeftBumper()

        if lb_pressed:
            if not hasattr(self, '_rt_locked_value'):
                self._rt_locked_value = right_trigger
            return self._rt_locked_value
        
        self._rt_locked_value = right_trigger  
        return right_trigger

    def with_deadband(self, value):
        if abs(value) < self.DEADBAND:
            return 0
        return (value - self.DEADBAND if value > 0 else value + self.DEADBAND) / (1 - self.DEADBAND)

    def get_left_trigger_locked(self):
        """
        Retorna o valor do Left Trigger normalmente, mas se o RB for pressionado,
        ele mantém o valor do Left Trigger no momento da pressão do RB.
        """
        pygame.event.pump()
        right_trigger = self.getLeftTrigger()
        lb_pressed = self.getRightBumper()

        if lb_pressed:
            if not hasattr(self, '_rt_locked_value'):
                self._rt_locked_value = right_trigger
            return self._rt_locked_value
        
        self._rt_locked_value = right_trigger
        return right_trigger


# if __name__ == "__main__":
#     try:
#         controller = XboxController()
#         print("Controle conectado!")
#         while True:
#             #inputs = (f"POVDown: {controller.getLeftStick()}, POVUp: {controller.getRightStick()}, POVLeft: {controller.getX()}, POVRight: {controller.getY()}")
#             inputs = (controller.get_right_trigger_locked())
#             print(inputs)
#     except Exception as e:
#         print(e)
