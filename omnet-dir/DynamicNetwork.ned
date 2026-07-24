network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        agent_central: AgentNode {
            xPos = 500.0;
            yPos = 500.0;
        }
        agent_p_1: AgentNode {
            xPos = 191.4;
            yPos = 779.86;
        }
        agent_p_2: AgentNode {
            xPos = 462.4;
            yPos = 432.93;
        }
        agent_p_3: AgentNode {
            xPos = 247.27;
            yPos = 229.87;
        }
        agent_p_4: AgentNode {
            xPos = 775.22;
            yPos = 846.7;
        }
        agent_p_5: AgentNode {
            xPos = 766.02;
            yPos = 81.81;
        }
        agent_p_6: AgentNode {
            xPos = 621.58;
            yPos = 873.33;
        }
        agent_p_7: AgentNode {
            xPos = 257.74;
            yPos = 257.24;
        }
        agent_p_8: AgentNode {
            xPos = 635.27;
            yPos = 846.08;
        }
        agent_p_9: AgentNode {
            xPos = 212.8;
            yPos = 764.88;
        }
        agent_p_10: AgentNode {
            xPos = 763.9;
            yPos = 423.55;
        }
        agent_p_11: AgentNode {
            xPos = 622.12;
            yPos = 936.78;
        }
        agent_p_12: AgentNode {
            xPos = 241.75;
            yPos = 591.63;
        }
        agent_p_13: AgentNode {
            xPos = 908.64;
            yPos = 574.3;
        }
        agent_p_14: AgentNode {
            xPos = 155.32;
            yPos = 870.2;
        }
        agent_p_15: AgentNode {
            xPos = 789.21;
            yPos = 561.44;
        }
        agent_p_16: AgentNode {
            xPos = 724.45;
            yPos = 783.13;
        }
        agent_p_17: AgentNode {
            xPos = 705.55;
            yPos = 371.07;
        }
        agent_p_18: AgentNode {
            xPos = 201.34;
            yPos = 737.76;
        }
        agent_p_19: AgentNode {
            xPos = 660.98;
            yPos = 843.34;
        }
        agent_p_20: AgentNode {
            xPos = 393.48;
            yPos = 654.65;
        }
        agent_p_21: AgentNode {
            xPos = 531.34;
            yPos = 782.03;
        }
        agent_p_22: AgentNode {
            xPos = 661.68;
            yPos = 223.42;
        }
        agent_p_23: AgentNode {
            xPos = 346.69;
            yPos = 220.72;
        }
        agent_p_24: AgentNode {
            xPos = 176.61;
            yPos = 104.76;
        }
        agent_p_25: AgentNode {
            xPos = 3.95;
            yPos = 989.01;
        }
        agent_p_26: AgentNode {
            xPos = 172.34;
            yPos = 708.33;
        }
        agent_p_27: AgentNode {
            xPos = 726.37;
            yPos = 193.59;
        }
        agent_p_28: AgentNode {
            xPos = 805.33;
            yPos = 440.38;
        }
        agent_p_29: AgentNode {
            xPos = 740.79;
            yPos = 577.23;
        }
        agent_p_30: AgentNode {
            xPos = 79.1;
            yPos = 890.52;
        }
        agent_p_31: AgentNode {
            xPos = 582.89;
            yPos = 936.14;
        }
        agent_p_32: AgentNode {
            xPos = 248.0;
            yPos = 332.38;
        }
        agent_p_33: AgentNode {
            xPos = 431.74;
            yPos = 665.01;
        }
        agent_p_34: AgentNode {
            xPos = 401.73;
            yPos = 698.66;
        }
        agent_p_35: AgentNode {
            xPos = 170.99;
            yPos = 657.62;
        }
        agent_p_36: AgentNode {
            xPos = 517.41;
            yPos = 235.79;
        }
        agent_p_37: AgentNode {
            xPos = 845.4;
            yPos = 813.13;
        }
        agent_p_38: AgentNode {
            xPos = 345.64;
            yPos = 89.89;
        }
        agent_p_39: AgentNode {
            xPos = 547.4;
            yPos = 209.2;
        }
        agent_p_40: AgentNode {
            xPos = 11.15;
            yPos = 893.8;
        }
        agent_p_41: AgentNode {
            xPos = 67.05;
            yPos = 578.36;
        }
        agent_p_42: AgentNode {
            xPos = 933.87;
            yPos = 631.32;
        }
        agent_p_43: AgentNode {
            xPos = 438.82;
            yPos = 736.45;
        }
        agent_p_44: AgentNode {
            xPos = 562.07;
            yPos = 882.37;
        }
        agent_p_45: AgentNode {
            xPos = 892.19;
            yPos = 267.71;
        }
        agent_p_46: AgentNode {
            xPos = 125.71;
            yPos = 659.66;
        }
        agent_p_47: AgentNode {
            xPos = 359.16;
            yPos = 804.55;
        }
        agent_p_48: AgentNode {
            xPos = 800.77;
            yPos = 260.34;
        }
        agent_p_49: AgentNode {
            xPos = 789.51;
            yPos = 17.68;
        }
        agent_p_50: AgentNode {
            xPos = 910.56;
            yPos = 302.89;
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
