network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        agent_central: AgentNode {
            xPos = 500.0;
            yPos = 500.0;
        }
        agent_p_1: AgentNode {
            xPos = 935.76;
            yPos = 977.47;
        }
        agent_p_2: AgentNode {
            xPos = 214.49;
            yPos = 331.13;
        }
        agent_p_3: AgentNode {
            xPos = 264.09;
            yPos = 149.59;
        }
        agent_p_4: AgentNode {
            xPos = 240.74;
            yPos = 416.01;
        }
        agent_p_5: AgentNode {
            xPos = 929.47;
            yPos = 604.2;
        }
        agent_p_6: AgentNode {
            xPos = 750.5;
            yPos = 387.23;
        }
        agent_p_7: AgentNode {
            xPos = 629.52;
            yPos = 993.78;
        }
        agent_p_8: AgentNode {
            xPos = 234.28;
            yPos = 773.44;
        }
        agent_p_9: AgentNode {
            xPos = 409.52;
            yPos = 963.01;
        }
        agent_p_10: AgentNode {
            xPos = 863.27;
            yPos = 663.29;
        }
        agent_p_11: AgentNode {
            xPos = 824.43;
            yPos = 658.87;
        }
        agent_p_12: AgentNode {
            xPos = 883.6;
            yPos = 865.96;
        }
        agent_p_13: AgentNode {
            xPos = 845.45;
            yPos = 227.6;
        }
        agent_p_14: AgentNode {
            xPos = 441.19;
            yPos = 95.72;
        }
        agent_p_15: AgentNode {
            xPos = 619.59;
            yPos = 811.21;
        }
        agent_p_16: AgentNode {
            xPos = 458.45;
            yPos = 595.22;
        }
        agent_p_17: AgentNode {
            xPos = 880.97;
            yPos = 533.52;
        }
        agent_p_18: AgentNode {
            xPos = 134.28;
            yPos = 763.22;
        }
        agent_p_19: AgentNode {
            xPos = 721.89;
            yPos = 134.1;
        }
        agent_p_20: AgentNode {
            xPos = 209.16;
            yPos = 634.02;
        }
        agent_p_21: AgentNode {
            xPos = 977.93;
            yPos = 248.33;
        }
        agent_p_22: AgentNode {
            xPos = 305.51;
            yPos = 699.56;
        }
        agent_p_23: AgentNode {
            xPos = 664.1;
            yPos = 861.88;
        }
        agent_p_24: AgentNode {
            xPos = 151.98;
            yPos = 234.83;
        }
        agent_p_25: AgentNode {
            xPos = 47.31;
            yPos = 597.25;
        }
        agent_p_26: AgentNode {
            xPos = 483.85;
            yPos = 247.04;
        }
        agent_p_27: AgentNode {
            xPos = 13.57;
            yPos = 869.32;
        }
        agent_p_28: AgentNode {
            xPos = 333.2;
            yPos = 47.7;
        }
        agent_p_29: AgentNode {
            xPos = 655.82;
            yPos = 123.86;
        }
        agent_p_30: AgentNode {
            xPos = 535.48;
            yPos = 618.01;
        }
        agent_p_31: AgentNode {
            xPos = 935.91;
            yPos = 803.42;
        }
        agent_p_32: AgentNode {
            xPos = 404.81;
            yPos = 933.87;
        }
        agent_p_33: AgentNode {
            xPos = 335.46;
            yPos = 56.04;
        }
        agent_p_34: AgentNode {
            xPos = 738.02;
            yPos = 674.75;
        }
        agent_p_35: AgentNode {
            xPos = 648.43;
            yPos = 477.92;
        }
        agent_p_36: AgentNode {
            xPos = 369.23;
            yPos = 183.5;
        }
        agent_p_37: AgentNode {
            xPos = 866.59;
            yPos = 65.4;
        }
        agent_p_38: AgentNode {
            xPos = 803.94;
            yPos = 966.5;
        }
        agent_p_39: AgentNode {
            xPos = 604.55;
            yPos = 810.69;
        }
        agent_p_40: AgentNode {
            xPos = 487.93;
            yPos = 423.72;
        }
        agent_p_41: AgentNode {
            xPos = 270.08;
            yPos = 888.0;
        }
        agent_p_42: AgentNode {
            xPos = 351.82;
            yPos = 510.39;
        }
        agent_p_43: AgentNode {
            xPos = 192.75;
            yPos = 87.36;
        }
        agent_p_44: AgentNode {
            xPos = 452.49;
            yPos = 987.89;
        }
        agent_p_45: AgentNode {
            xPos = 632.55;
            yPos = 429.45;
        }
        agent_p_46: AgentNode {
            xPos = 309.07;
            yPos = 904.23;
        }
        agent_p_47: AgentNode {
            xPos = 395.26;
            yPos = 14.49;
        }
        agent_p_48: AgentNode {
            xPos = 217.76;
            yPos = 421.91;
        }
        agent_p_49: AgentNode {
            xPos = 463.01;
            yPos = 369.83;
        }
        agent_p_50: AgentNode {
            xPos = 736.95;
            yPos = 199.28;
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
