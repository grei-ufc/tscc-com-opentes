network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        agent_central: AgentNode {
            xPos = 500.0;
            yPos = 500.0;
        }
        agent_p_1: AgentNode {
            xPos = 151.94;
            yPos = 278.38;
        }
        agent_p_2: AgentNode {
            xPos = 647.9;
            yPos = 619.32;
        }
        agent_p_3: AgentNode {
            xPos = 419.64;
            yPos = 56.14;
        }
        agent_p_4: AgentNode {
            xPos = 114.31;
            yPos = 377.81;
        }
        agent_p_5: AgentNode {
            xPos = 204.64;
            yPos = 719.6;
        }
        agent_p_6: AgentNode {
            xPos = 69.61;
            yPos = 570.38;
        }
        agent_p_7: AgentNode {
            xPos = 872.35;
            yPos = 391.01;
        }
        agent_p_8: AgentNode {
            xPos = 700.0;
            yPos = 308.49;
        }
        agent_p_9: AgentNode {
            xPos = 62.41;
            yPos = 436.75;
        }
        agent_p_10: AgentNode {
            xPos = 87.18;
            yPos = 360.17;
        }
        agent_p_11: AgentNode {
            xPos = 245.89;
            yPos = 495.67;
        }
        agent_p_12: AgentNode {
            xPos = 266.91;
            yPos = 612.46;
        }
        agent_p_13: AgentNode {
            xPos = 700.91;
            yPos = 563.95;
        }
        agent_p_14: AgentNode {
            xPos = 733.32;
            yPos = 231.82;
        }
        agent_p_15: AgentNode {
            xPos = 83.93;
            yPos = 627.52;
        }
        agent_p_16: AgentNode {
            xPos = 602.26;
            yPos = 946.08;
        }
        agent_p_17: AgentNode {
            xPos = 426.44;
            yPos = 759.68;
        }
        agent_p_18: AgentNode {
            xPos = 379.4;
            yPos = 69.64;
        }
        agent_p_19: AgentNode {
            xPos = 866.91;
            yPos = 507.27;
        }
        agent_p_20: AgentNode {
            xPos = 755.57;
            yPos = 302.31;
        }

    connections:
        agent_central.port++ <--> Link_Wired <--> agent_p_1.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_2.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_3.port++;
        agent_central.port++ <--> Link_2G <--> agent_p_4.port++;
        agent_central.port++ <--> Link_Wireless <--> agent_p_5.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_6.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_7.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_8.port++;
        agent_central.port++ <--> Link_2G <--> agent_p_9.port++;
        agent_central.port++ <--> Link_Wireless <--> agent_p_10.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_11.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_12.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_13.port++;
        agent_central.port++ <--> Link_2G <--> agent_p_14.port++;
        agent_central.port++ <--> Link_Wireless <--> agent_p_15.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_16.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_17.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_18.port++;
        agent_central.port++ <--> Link_2G <--> agent_p_19.port++;
        agent_central.port++ <--> Link_Wireless <--> agent_p_20.port++;
}
