#include <vector>
#include "Command.h"
#include "SubsystemBase.h"

class CommandScheduler {
private:
    std::vector<SubsystemBase*> subsystems;
    std::vector<Command*> activeCommands;

    // Construtor privado (padrão Singleton)
    CommandScheduler() {} 

public:
    // Pega a instância única do Scheduler
    static CommandScheduler& getInstance() {
        static CommandScheduler instance;
        return instance;
    }

    void registerSubsystem(SubsystemBase* subsystem) {
        subsystems.push_back(subsystem);
    }

    void schedule(Command* command) {
        command->initialize();
        activeCommands.push_back(command);
    }

    // O motor que faz tudo girar!
    void run() {
        // 1. Roda o periodic de todos os subsystems
        for (auto sub : subsystems) {
            sub->periodic();
        }

        // 2. Roda os comandos ativos
        for (auto it = activeCommands.begin(); it != activeCommands.end(); ) {
            Command* cmd = *it;
            cmd->execute();

            if (cmd->isFinished()) {
                cmd->end(false); // Terminou naturalmente
                it = activeCommands.erase(it); // Remove da lista de execução
            } else {
                ++it;
            }
        }
    }
};