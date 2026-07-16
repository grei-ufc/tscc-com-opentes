network DynamicNetwork
{
    submodules:
        mosaikBridge: MosaikBridge;

        agent_central: AgentNode {
            agent_id = "agent_central";
        }
        agent_p_1: AgentNode {
            agent_id = "agent_p_1";
        }
        agent_p_2: AgentNode {
            agent_id = "agent_p_2";
        }
        agent_p_3: AgentNode {
            agent_id = "agent_p_3";
        }
        agent_p_4: AgentNode {
            agent_id = "agent_p_4";
        }
        agent_p_5: AgentNode {
            agent_id = "agent_p_5";
        }
        agent_p_6: AgentNode {
            agent_id = "agent_p_6";
        }
        agent_p_7: AgentNode {
            agent_id = "agent_p_7";
        }
        agent_p_8: AgentNode {
            agent_id = "agent_p_8";
        }
        agent_p_9: AgentNode {
            agent_id = "agent_p_9";
        }
        agent_p_10: AgentNode {
            agent_id = "agent_p_10";
        }
        agent_p_11: AgentNode {
            agent_id = "agent_p_11";
        }
        agent_p_12: AgentNode {
            agent_id = "agent_p_12";
        }
        agent_p_13: AgentNode {
            agent_id = "agent_p_13";
        }
        agent_p_14: AgentNode {
            agent_id = "agent_p_14";
        }
        agent_p_15: AgentNode {
            agent_id = "agent_p_15";
        }
        agent_p_16: AgentNode {
            agent_id = "agent_p_16";
        }
        agent_p_17: AgentNode {
            agent_id = "agent_p_17";
        }
        agent_p_18: AgentNode {
            agent_id = "agent_p_18";
        }
        agent_p_19: AgentNode {
            agent_id = "agent_p_19";
        }
        agent_p_20: AgentNode {
            agent_id = "agent_p_20";
        }
        agent_p_21: AgentNode {
            agent_id = "agent_p_21";
        }
        agent_p_22: AgentNode {
            agent_id = "agent_p_22";
        }
        agent_p_23: AgentNode {
            agent_id = "agent_p_23";
        }
        agent_p_24: AgentNode {
            agent_id = "agent_p_24";
        }
        agent_p_25: AgentNode {
            agent_id = "agent_p_25";
        }
        agent_p_26: AgentNode {
            agent_id = "agent_p_26";
        }
        agent_p_27: AgentNode {
            agent_id = "agent_p_27";
        }
        agent_p_28: AgentNode {
            agent_id = "agent_p_28";
        }
        agent_p_29: AgentNode {
            agent_id = "agent_p_29";
        }
        agent_p_30: AgentNode {
            agent_id = "agent_p_30";
        }
        agent_p_31: AgentNode {
            agent_id = "agent_p_31";
        }
        agent_p_32: AgentNode {
            agent_id = "agent_p_32";
        }
        agent_p_33: AgentNode {
            agent_id = "agent_p_33";
        }
        agent_p_34: AgentNode {
            agent_id = "agent_p_34";
        }
        agent_p_35: AgentNode {
            agent_id = "agent_p_35";
        }
        agent_p_36: AgentNode {
            agent_id = "agent_p_36";
        }
        agent_p_37: AgentNode {
            agent_id = "agent_p_37";
        }
        agent_p_38: AgentNode {
            agent_id = "agent_p_38";
        }
        agent_p_39: AgentNode {
            agent_id = "agent_p_39";
        }
        agent_p_40: AgentNode {
            agent_id = "agent_p_40";
        }
        agent_p_41: AgentNode {
            agent_id = "agent_p_41";
        }
        agent_p_42: AgentNode {
            agent_id = "agent_p_42";
        }
        agent_p_43: AgentNode {
            agent_id = "agent_p_43";
        }
        agent_p_44: AgentNode {
            agent_id = "agent_p_44";
        }
        agent_p_45: AgentNode {
            agent_id = "agent_p_45";
        }
        agent_p_46: AgentNode {
            agent_id = "agent_p_46";
        }
        agent_p_47: AgentNode {
            agent_id = "agent_p_47";
        }
        agent_p_48: AgentNode {
            agent_id = "agent_p_48";
        }
        agent_p_49: AgentNode {
            agent_id = "agent_p_49";
        }
        agent_p_50: AgentNode {
            agent_id = "agent_p_50";
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
