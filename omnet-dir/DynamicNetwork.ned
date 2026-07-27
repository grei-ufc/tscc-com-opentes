network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        agent_central: AgentNode {
            xPos = 500.0;
            yPos = 500.0;
        }
        agent_p_1: AgentNode {
            xPos = 436.1;
            yPos = 511.53;
        }
        agent_p_2: AgentNode {
            xPos = 769.61;
            yPos = 362.93;
        }
        agent_p_3: AgentNode {
            xPos = 778.88;
            yPos = 814.56;
        }
        agent_p_4: AgentNode {
            xPos = 133.58;
            yPos = 385.96;
        }
        agent_p_5: AgentNode {
            xPos = 370.88;
            yPos = 34.75;
        }
        agent_p_6: AgentNode {
            xPos = 742.83;
            yPos = 302.14;
        }
        agent_p_7: AgentNode {
            xPos = 726.16;
            yPos = 685.96;
        }
        agent_p_8: AgentNode {
            xPos = 344.86;
            yPos = 823.68;
        }
        agent_p_9: AgentNode {
            xPos = 853.44;
            yPos = 989.98;
        }
        agent_p_10: AgentNode {
            xPos = 795.14;
            yPos = 244.25;
        }
        agent_p_11: AgentNode {
            xPos = 173.31;
            yPos = 744.49;
        }
        agent_p_12: AgentNode {
            xPos = 500.51;
            yPos = 906.91;
        }
        agent_p_13: AgentNode {
            xPos = 148.68;
            yPos = 318.93;
        }
        agent_p_14: AgentNode {
            xPos = 966.91;
            yPos = 200.78;
        }
        agent_p_15: AgentNode {
            xPos = 450.16;
            yPos = 901.5;
        }
        agent_p_16: AgentNode {
            xPos = 296.44;
            yPos = 971.39;
        }
        agent_p_17: AgentNode {
            xPos = 406.06;
            yPos = 986.24;
        }
        agent_p_18: AgentNode {
            xPos = 679.59;
            yPos = 437.74;
        }
        agent_p_19: AgentNode {
            xPos = 796.3;
            yPos = 899.79;
        }
        agent_p_20: AgentNode {
            xPos = 826.46;
            yPos = 808.68;
        }
        agent_p_21: AgentNode {
            xPos = 466.28;
            yPos = 314.81;
        }
        agent_p_22: AgentNode {
            xPos = 464.28;
            yPos = 554.06;
        }
        agent_p_23: AgentNode {
            xPos = 85.91;
            yPos = 33.36;
        }
        agent_p_24: AgentNode {
            xPos = 894.16;
            yPos = 623.82;
        }
        agent_p_25: AgentNode {
            xPos = 682.4;
            yPos = 86.38;
        }
        agent_p_26: AgentNode {
            xPos = 370.95;
            yPos = 908.68;
        }
        agent_p_27: AgentNode {
            xPos = 493.88;
            yPos = 635.15;
        }
        agent_p_28: AgentNode {
            xPos = 57.04;
            yPos = 85.09;
        }
        agent_p_29: AgentNode {
            xPos = 865.1;
            yPos = 375.81;
        }
        agent_p_30: AgentNode {
            xPos = 70.01;
            yPos = 502.52;
        }
        agent_p_31: AgentNode {
            xPos = 720.94;
            yPos = 556.14;
        }
        agent_p_32: AgentNode {
            xPos = 714.53;
            yPos = 725.91;
        }
        agent_p_33: AgentNode {
            xPos = 313.75;
            yPos = 557.32;
        }
        agent_p_34: AgentNode {
            xPos = 649.39;
            yPos = 742.15;
        }
        agent_p_35: AgentNode {
            xPos = 14.92;
            yPos = 182.94;
        }
        agent_p_36: AgentNode {
            xPos = 168.26;
            yPos = 816.34;
        }
        agent_p_37: AgentNode {
            xPos = 949.58;
            yPos = 308.22;
        }
        agent_p_38: AgentNode {
            xPos = 995.22;
            yPos = 955.5;
        }
        agent_p_39: AgentNode {
            xPos = 380.35;
            yPos = 859.93;
        }
        agent_p_40: AgentNode {
            xPos = 617.73;
            yPos = 542.45;
        }
        agent_p_41: AgentNode {
            xPos = 780.68;
            yPos = 930.79;
        }
        agent_p_42: AgentNode {
            xPos = 247.15;
            yPos = 627.95;
        }
        agent_p_43: AgentNode {
            xPos = 736.73;
            yPos = 966.56;
        }
        agent_p_44: AgentNode {
            xPos = 107.52;
            yPos = 576.28;
        }
        agent_p_45: AgentNode {
            xPos = 238.99;
            yPos = 709.77;
        }
        agent_p_46: AgentNode {
            xPos = 299.89;
            yPos = 540.24;
        }
        agent_p_47: AgentNode {
            xPos = 212.59;
            yPos = 271.37;
        }
        agent_p_48: AgentNode {
            xPos = 495.44;
            yPos = 238.62;
        }
        agent_p_49: AgentNode {
            xPos = 566.61;
            yPos = 358.65;
        }
        agent_p_50: AgentNode {
            xPos = 108.64;
            yPos = 233.65;
        }

    connections:
        agent_central.port++ <--> Link_5G <--> agent_p_1.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_2.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_3.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_4.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_5.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_6.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_7.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_8.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_9.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_10.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_11.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_12.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_13.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_14.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_15.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_16.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_17.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_18.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_19.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_20.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_21.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_22.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_23.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_24.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_25.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_26.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_27.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_28.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_29.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_30.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_31.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_32.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_33.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_34.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_35.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_36.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_37.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_38.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_39.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_40.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_41.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_42.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_43.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_44.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_45.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_46.port++;
        agent_central.port++ <--> Link_Wired <--> agent_p_47.port++;
        agent_central.port++ <--> Link_IoT <--> agent_p_48.port++;
        agent_central.port++ <--> Link_5G <--> agent_p_49.port++;
        agent_central.port++ <--> Link_4G <--> agent_p_50.port++;
}
