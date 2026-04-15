#include <vector>
#include "src/main/cpp/lib/SubsystemBase.h"

class Command {
protected:
    std::vector<SubsystemBase*> m_requirements;

public:
    virtual ~Command() {}

    virtual void initialize() {}
    virtual void execute() {}
    virtual bool isFinished() { return false; }
    virtual void end(bool interrupted) {}

    void addRequirements(SubsystemBase* subsystem) {
        m_requirements.push_back(subsystem);
    }

    std::vector<SubsystemBase*> getRequirements() {
        return m_requirements;
    }
};