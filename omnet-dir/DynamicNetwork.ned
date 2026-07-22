network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        agent_central: AgentNode {
            xPos = 500.0;
            yPos = 500.0;
        }
        agent_p_1: AgentNode {
            xPos = 987.51;
            yPos = 390.12;
        }
        agent_p_2: AgentNode {
            xPos = 289.77;
            yPos = 680.81;
        }
        agent_p_3: AgentNode {
            xPos = 947.11;
            yPos = 133.59;
        }
        agent_p_4: AgentNode {
            xPos = 353.22;
            yPos = 211.11;
        }
        agent_p_5: AgentNode {
            xPos = 244.42;
            yPos = 263.82;
        }
        agent_p_6: AgentNode {
            xPos = 29.98;
            yPos = 377.11;
        }
        agent_p_7: AgentNode {
            xPos = 672.77;
            yPos = 193.91;
        }
        agent_p_8: AgentNode {
            xPos = 319.65;
            yPos = 204.06;
        }
        agent_p_9: AgentNode {
            xPos = 86.92;
            yPos = 722.61;
        }
        agent_p_10: AgentNode {
            xPos = 56.09;
            yPos = 913.68;
        }
        agent_p_11: AgentNode {
            xPos = 137.72;
            yPos = 568.15;
        }
        agent_p_12: AgentNode {
            xPos = 334.15;
            yPos = 21.95;
        }
        agent_p_13: AgentNode {
            xPos = 718.1;
            yPos = 704.52;
        }
        agent_p_14: AgentNode {
            xPos = 23.87;
            yPos = 42.68;
        }
        agent_p_15: AgentNode {
            xPos = 30.09;
            yPos = 134.36;
        }
        agent_p_16: AgentNode {
            xPos = 311.24;
            yPos = 438.76;
        }
        agent_p_17: AgentNode {
            xPos = 483.23;
            yPos = 975.64;
        }
        agent_p_18: AgentNode {
            xPos = 524.18;
            yPos = 65.94;
        }
        agent_p_19: AgentNode {
            xPos = 624.97;
            yPos = 778.66;
        }
        agent_p_20: AgentNode {
            xPos = 645.4;
            yPos = 238.46;
        }
        agent_p_21: AgentNode {
            xPos = 729.5;
            yPos = 492.17;
        }
        agent_p_22: AgentNode {
            xPos = 200.87;
            yPos = 747.24;
        }
        agent_p_23: AgentNode {
            xPos = 666.34;
            yPos = 504.03;
        }
        agent_p_24: AgentNode {
            xPos = 661.31;
            yPos = 382.76;
        }
        agent_p_25: AgentNode {
            xPos = 962.13;
            yPos = 864.91;
        }
        agent_p_26: AgentNode {
            xPos = 351.55;
            yPos = 146.61;
        }
        agent_p_27: AgentNode {
            xPos = 193.98;
            yPos = 134.84;
        }
        agent_p_28: AgentNode {
            xPos = 337.56;
            yPos = 416.83;
        }
        agent_p_29: AgentNode {
            xPos = 788.95;
            yPos = 579.12;
        }
        agent_p_30: AgentNode {
            xPos = 911.33;
            yPos = 192.43;
        }
        agent_p_31: AgentNode {
            xPos = 619.1;
            yPos = 307.88;
        }
        agent_p_32: AgentNode {
            xPos = 491.51;
            yPos = 750.58;
        }
        agent_p_33: AgentNode {
            xPos = 141.34;
            yPos = 924.25;
        }
        agent_p_34: AgentNode {
            xPos = 96.66;
            yPos = 495.25;
        }
        agent_p_35: AgentNode {
            xPos = 220.67;
            yPos = 585.96;
        }
        agent_p_36: AgentNode {
            xPos = 493.14;
            yPos = 840.24;
        }
        agent_p_37: AgentNode {
            xPos = 931.39;
            yPos = 585.85;
        }
        agent_p_38: AgentNode {
            xPos = 462.49;
            yPos = 285.63;
        }
        agent_p_39: AgentNode {
            xPos = 790.74;
            yPos = 267.8;
        }
        agent_p_40: AgentNode {
            xPos = 529.93;
            yPos = 925.17;
        }
        agent_p_41: AgentNode {
            xPos = 262.66;
            yPos = 165.56;
        }
        agent_p_42: AgentNode {
            xPos = 990.23;
            yPos = 751.46;
        }
        agent_p_43: AgentNode {
            xPos = 980.13;
            yPos = 337.08;
        }
        agent_p_44: AgentNode {
            xPos = 852.02;
            yPos = 566.75;
        }
        agent_p_45: AgentNode {
            xPos = 239.81;
            yPos = 13.66;
        }
        agent_p_46: AgentNode {
            xPos = 71.48;
            yPos = 811.6;
        }
        agent_p_47: AgentNode {
            xPos = 843.19;
            yPos = 341.41;
        }
        agent_p_48: AgentNode {
            xPos = 1.56;
            yPos = 862.97;
        }
        agent_p_49: AgentNode {
            xPos = 878.81;
            yPos = 6.3;
        }
        agent_p_50: AgentNode {
            xPos = 21.25;
            yPos = 511.1;
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
