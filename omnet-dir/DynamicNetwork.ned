network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        agent_central: AgentNode {
            xPos = 500.0;
            yPos = 500.0;
        }
        agent_p_1: AgentNode {
            xPos = 639.43;
            yPos = 25.01;
        }
        agent_p_2: AgentNode {
            xPos = 275.03;
            yPos = 223.21;
        }
        agent_p_3: AgentNode {
            xPos = 736.47;
            yPos = 676.7;
        }
        agent_p_4: AgentNode {
            xPos = 892.18;
            yPos = 86.94;
        }
        agent_p_5: AgentNode {
            xPos = 421.92;
            yPos = 29.8;
        }
        agent_p_6: AgentNode {
            xPos = 218.64;
            yPos = 505.36;
        }
        agent_p_7: AgentNode {
            xPos = 26.54;
            yPos = 198.84;
        }
        agent_p_8: AgentNode {
            xPos = 649.88;
            yPos = 544.94;
        }
        agent_p_9: AgentNode {
            xPos = 220.44;
            yPos = 589.27;
        }
        agent_p_10: AgentNode {
            xPos = 809.43;
            yPos = 6.5;
        }
        agent_p_11: AgentNode {
            xPos = 805.82;
            yPos = 698.14;
        }
        agent_p_12: AgentNode {
            xPos = 340.25;
            yPos = 155.48;
        }
        agent_p_13: AgentNode {
            xPos = 957.21;
            yPos = 336.59;
        }
        agent_p_14: AgentNode {
            xPos = 92.75;
            yPos = 96.72;
        }
        agent_p_15: AgentNode {
            xPos = 847.49;
            yPos = 603.73;
        }
        agent_p_16: AgentNode {
            xPos = 807.13;
            yPos = 729.73;
        }
        agent_p_17: AgentNode {
            xPos = 536.23;
            yPos = 973.12;
        }
        agent_p_18: AgentNode {
            xPos = 378.53;
            yPos = 552.04;
        }
        agent_p_19: AgentNode {
            xPos = 829.4;
            yPos = 618.52;
        }
        agent_p_20: AgentNode {
            xPos = 861.71;
            yPos = 577.35;
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
