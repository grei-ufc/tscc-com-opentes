network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        agente_1: AgentNode {
            agent_id = "agente_1";
            xPos = 200.0;
            yPos = 500.0;
        }
        agente_2: AgentNode {
            agent_id = "agente_2";
            xPos = 500.0;
            yPos = 800.0;
        }
        agente_3: AgentNode {
            agent_id = "agente_3";
            xPos = 800.0;
            yPos = 500.0;
        }
        agente_4: AgentNode {
            agent_id = "agente_4";
            xPos = 500.0;
            yPos = 200.0;
        }

    connections:
        agente_1.port++ <--> Link_Wired <--> agente_2.port++;
        agente_2.port++ <--> Link_4G <--> agente_3.port++;
        agente_3.port++ <--> Link_5G <--> agente_4.port++;
        agente_4.port++ <--> Link_2G <--> agente_1.port++;
}
