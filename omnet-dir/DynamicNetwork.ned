network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        agent_0: AgentNode {
            xPos = 0.0;
            yPos = 0.0;
        }
        agent_dso: AgentNode {
            xPos = 0.0;
            yPos = 0.0;
        }
        agent_market: AgentNode {
            xPos = 0.0;
            yPos = 0.0;
        }
        agent_611: AgentNode {
            xPos = -182.88;
            yPos = -1221.2;
        }
        agent_632: AgentNode {
            xPos = 0.0;
            yPos = -611.6;
        }
        agent_633: AgentNode {
            xPos = 152.4;
            yPos = -611.6;
        }
        agent_634: AgentNode {
            xPos = 153.4;
            yPos = -611.6;
        }
        agent_645: AgentNode {
            xPos = -152.4;
            yPos = -611.6;
        }
        agent_646: AgentNode {
            xPos = -243.84;
            yPos = -611.6;
        }
        agent_650: AgentNode {
            xPos = 0.0;
            yPos = -1.0;
        }
        agent_652: AgentNode {
            xPos = -91.44;
            yPos = -1465.04;
        }
        agent_660: AgentNode {
            xPos = 0.0;
            yPos = -2.0;
        }
        agent_670: AgentNode {
            xPos = 0.0;
            yPos = -814.9;
        }
        agent_671: AgentNode {
            xPos = 0.0;
            yPos = -1221.2;
        }
        agent_675: AgentNode {
            xPos = 153.4;
            yPos = -1221.2;
        }
        agent_680: AgentNode {
            xPos = 0.0;
            yPos = -1526.0;
        }
        agent_684: AgentNode {
            xPos = -91.44;
            yPos = -1221.2;
        }
        agent_692: AgentNode {
            xPos = 1.0;
            yPos = -1221.2;
        }

    connections:
        agent_0.port++ <--> Link_Wired <--> agent_dso.port++;
        agent_0.port++ <--> Link_6TiSCH <--> agent_market.port++;
        agent_0.port++ <--> Link_WiSUN <--> agent_611.port++;
        agent_0.port++ <--> Link_Wired <--> agent_632.port++;
        agent_0.port++ <--> Link_6TiSCH <--> agent_633.port++;
        agent_0.port++ <--> Link_WiSUN <--> agent_634.port++;
        agent_0.port++ <--> Link_Wired <--> agent_645.port++;
        agent_0.port++ <--> Link_6TiSCH <--> agent_646.port++;
        agent_0.port++ <--> Link_WiSUN <--> agent_650.port++;
        agent_0.port++ <--> Link_Wired <--> agent_652.port++;
        agent_0.port++ <--> Link_6TiSCH <--> agent_660.port++;
        agent_0.port++ <--> Link_WiSUN <--> agent_670.port++;
        agent_0.port++ <--> Link_Wired <--> agent_671.port++;
        agent_0.port++ <--> Link_6TiSCH <--> agent_675.port++;
        agent_0.port++ <--> Link_WiSUN <--> agent_680.port++;
        agent_0.port++ <--> Link_Wired <--> agent_684.port++;
        agent_0.port++ <--> Link_6TiSCH <--> agent_692.port++;
}
