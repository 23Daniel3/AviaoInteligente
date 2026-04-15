#include <Arduino.h>

class SubsystemBase {
public:
    virtual ~SubsystemBase() {} // Destrutor virtual é boa prática em C++
    
    // Método que será chamado em todo ciclo do loop (igual no Java)
    virtual void periodic() {} 
};