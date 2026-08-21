network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        agent_central: AgentNode {
            xPos = 500.0;
            yPos = 500.0;
        }
        agent_p_1: AgentNode {
            xPos = 868.38;
            yPos = 122.41;
        }
        agent_p_2: AgentNode {
            xPos = 125.72;
            yPos = 246.44;
        }
        agent_p_3: AgentNode {
            xPos = 165.5;
            yPos = 923.4;
        }

    connections:
        agent_central.port++ <--> Link_5G <--> agent_p_1.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_2.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_3.port++;
}
