network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        agente_1: AgentNode {
            xPos = 850.0;
            yPos = 500.0;
        }
        agente_2: AgentNode {
            xPos = 832.87;
            yPos = 608.16;
        }
        agente_3: AgentNode {
            xPos = 783.16;
            yPos = 705.72;
        }
        agente_4: AgentNode {
            xPos = 705.72;
            yPos = 783.16;
        }
        agente_5: AgentNode {
            xPos = 608.16;
            yPos = 832.87;
        }
        agente_6: AgentNode {
            xPos = 500.0;
            yPos = 850.0;
        }
        agente_7: AgentNode {
            xPos = 391.84;
            yPos = 832.87;
        }
        agente_8: AgentNode {
            xPos = 294.28;
            yPos = 783.16;
        }
        agente_9: AgentNode {
            xPos = 216.84;
            yPos = 705.72;
        }
        agente_10: AgentNode {
            xPos = 167.13;
            yPos = 608.16;
        }
        agente_11: AgentNode {
            xPos = 150.0;
            yPos = 500.0;
        }
        agente_12: AgentNode {
            xPos = 167.13;
            yPos = 391.84;
        }
        agente_13: AgentNode {
            xPos = 216.84;
            yPos = 294.28;
        }
        agente_14: AgentNode {
            xPos = 294.28;
            yPos = 216.84;
        }
        agente_15: AgentNode {
            xPos = 391.84;
            yPos = 167.13;
        }
        agente_16: AgentNode {
            xPos = 500.0;
            yPos = 150.0;
        }
        agente_17: AgentNode {
            xPos = 608.16;
            yPos = 167.13;
        }
        agente_18: AgentNode {
            xPos = 705.72;
            yPos = 216.84;
        }
        agente_19: AgentNode {
            xPos = 783.16;
            yPos = 294.28;
        }
        agente_20: AgentNode {
            xPos = 832.87;
            yPos = 391.84;
        }

    connections:
        agente_1.port++ <--> Link_Wired <--> agente_2.port++;
        agente_2.port++ <--> Link_5G <--> agente_3.port++;
        agente_3.port++ <--> Link_Wireless <--> agente_4.port++;
        agente_4.port++ <--> Link_4G <--> agente_5.port++;
        agente_5.port++ <--> Link_2G <--> agente_6.port++;
        agente_6.port++ <--> Link_Wired <--> agente_7.port++;
        agente_7.port++ <--> Link_5G <--> agente_8.port++;
        agente_8.port++ <--> Link_Wireless <--> agente_9.port++;
        agente_9.port++ <--> Link_4G <--> agente_10.port++;
        agente_10.port++ <--> Link_2G <--> agente_11.port++;
        agente_11.port++ <--> Link_Wired <--> agente_12.port++;
        agente_12.port++ <--> Link_5G <--> agente_13.port++;
        agente_13.port++ <--> Link_Wireless <--> agente_14.port++;
        agente_14.port++ <--> Link_4G <--> agente_15.port++;
        agente_15.port++ <--> Link_2G <--> agente_16.port++;
        agente_16.port++ <--> Link_Wired <--> agente_17.port++;
        agente_17.port++ <--> Link_5G <--> agente_18.port++;
        agente_18.port++ <--> Link_Wireless <--> agente_19.port++;
        agente_19.port++ <--> Link_4G <--> agente_20.port++;
        agente_20.port++ <--> Link_2G <--> agente_1.port++;
}
