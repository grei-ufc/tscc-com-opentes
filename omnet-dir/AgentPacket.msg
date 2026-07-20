
cplusplus {{
#include <omnetpp.h>
}}

// Define o pacote customizado
packet AgentPacket {
    string srcAgent;   // ID do agente de origem (ex: "agent_0")
    string destAgent;  // ID do agente de destino (ex: "agent_1")
    string payload;    // O JSON original da mensagem FIPA-ACL
}