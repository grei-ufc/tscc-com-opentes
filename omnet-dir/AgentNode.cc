/**
 * @file AgentNode.cc
 * @brief Física de Redes Realista: Filas, Atraso Espacial, Jitter por Ruído 
 * e Perda de Pacotes no Receptor (Demodulação) via Atenuação de Distância.
 */

#include <omnetpp.h>
#include <map>
#include <string>
#include <vector>
#include <cmath>
#include <nlohmann/json.hpp>
#include "AgentPacket_m.h"

using namespace omnetpp;
using json = nlohmann::json;

class AgentNode : public cSimpleModule
{
  private:
    std::string myAgentId;
    std::map<std::string, int> routingTable; 
    std::map<int, cPacketQueue*> txQueues;
    std::map<int, cMessage*> endTxMsgs;
    
    std::map<std::string, double> lastLatencies;
    std::map<int, double> baseChannelDelays; 
    
    // Novo: Mapeia a chance do pacote ser destruído ao chegar deste vizinho
    std::map<std::string, double> inDropChances; 

  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void handleParameterChange(const char *parname) override;
    virtual ~AgentNode(); 

    void processInjectedData();
    void transmitPacket(AgentPacket *pkt, int portIndex);
    std::vector<std::string> splitString(const std::string& s, const std::string& delimiter);
    std::string mapPadeToOmnet(const std::string& padeId);
};

Define_Module(AgentNode);

void AgentNode::initialize()
{
    myAgentId = getName(); 
    EV << "AgentNode " << myAgentId << " inicializado." << std::endl;
    
    double myX = par("xPos").doubleValue();
    double myY = par("yPos").doubleValue();

    int numPorts = gateSize("port");
    for (int i = 0; i < numPorts; i++) {
        txQueues[i] = new cPacketQueue(("txQueue_" + std::to_string(i)).c_str());
        
        cMessage *endTxMsg = new cMessage(("endTx_" + std::to_string(i)).c_str());
        endTxMsg->setContextPointer((void *)(intptr_t)i); 
        endTxMsgs[i] = endTxMsg;

        cGate *outGate = gate("port$o", i);
        if (outGate->getPathEndGate() != nullptr) {
            cModule *neighbor = outGate->getPathEndGate()->getOwnerModule();
            std::string neighborId = neighbor->getName();
            routingTable[neighborId] = i; 
            
            if (neighbor->hasPar("xPos") && neighbor->hasPar("yPos")) {
                double nX = neighbor->par("xPos").doubleValue();
                double nY = neighbor->par("yPos").doubleValue();
                double dist = std::sqrt(std::pow(nX - myX, 2) + std::pow(nY - myY, 2));
                
                cDelayChannel *delayChannel = dynamic_cast<cDelayChannel*>(outGate->getTransmissionChannel());
                if (delayChannel) {
                    double currentDelay = delayChannel->getDelay().dbl();
                    double propagationDelay = dist * 0.00005; 
                    baseChannelDelays[i] = currentDelay + propagationDelay;
                    delayChannel->setDelay(baseChannelDelays[i]);
                } else {
                    baseChannelDelays[i] = 0.0;
                }
                
                // ==============================================================
                // ATENUAÇÃO NA RECEPÇÃO: O nó calcula a distância deste vizinho
                // e define a taxa de erro (1.5% de chance de drop a cada 100m)
                // ==============================================================
                inDropChances[neighborId] = (dist / 100.0) * 0.015;
            }
        }
    }
}

AgentNode::~AgentNode() {
    for (auto const& pair : txQueues) delete pair.second;
    for (auto const& pair : endTxMsgs) cancelAndDelete(pair.second);
}

void AgentNode::handleParameterChange(const char *parname) {
    if (std::string(parname) == "val_in" && !std::string(par("val_in").stdstringValue()).empty()) {
        processInjectedData();
    }
}

std::string AgentNode::mapPadeToOmnet(const std::string& padeId) {
    if (padeId == "AgenteCentral") return "agent_central";
    if (padeId.find("AgenteP_") == 0) return "agent_p_" + padeId.substr(8);
    return "";
}

void AgentNode::transmitPacket(AgentPacket *pkt, int portIndex) {
    cChannel *channel = gate("port$o", portIndex)->getTransmissionChannel();
    if (!channel->isBusy() && txQueues[portIndex]->isEmpty()) {
        cDelayChannel *delayChannel = dynamic_cast<cDelayChannel*>(channel);
        if (delayChannel) {
            double baseDelay = baseChannelDelays[portIndex];
            double noise = (baseDelay > 0.0015) ? uniform(0, baseDelay * 0.25) : 0.0;
            delayChannel->setDelay(std::max(0.0001, baseDelay + noise)); 
        }
        send(pkt, "port$o", portIndex); 
        scheduleAt(channel->getTransmissionFinishTime(), endTxMsgs[portIndex]);
    } else {
        txQueues[portIndex]->insert(pkt);
    }
}

void AgentNode::processInjectedData() {
    std::string current_in = par("val_in").stdstringValue();
    par("val_in").setStringValue(""); 
    std::vector<std::string> messages = splitString(current_in, "|||");

    for (const std::string& msg_str : messages) {
        try {
            json jMsg = json::parse(msg_str);
            if (jMsg.contains("receivers")) {
                for (auto& rec : jMsg["receivers"]) {
                    std::string rawReceiver = rec.get<std::string>();
                    std::string padeId = rawReceiver.substr(0, rawReceiver.find('@'));
                    std::string destId = mapPadeToOmnet(padeId);
                    
                    if (destId.empty() || destId == myAgentId) continue;

                    if (routingTable.find(destId) != routingTable.end()) {
                        AgentPacket *pkt = new AgentPacket(msg_str.c_str());
                        pkt->setSrcAgent(myAgentId.c_str());
                        pkt->setDestAgent(destId.c_str());
                        pkt->setPayload(msg_str.c_str()); 
                        pkt->setByteLength(msg_str.length());
                        transmitPacket(pkt, routingTable[destId]);
                        par("packets_sent") = par("packets_sent").doubleValue() + 1;
                    }
                }
            }
        } catch (...) {}
    }
}

void AgentNode::handleMessage(cMessage *msg) {
    if (msg->isSelfMessage()) {
        int portIndex = (int)(intptr_t)msg->getContextPointer();
        if (!txQueues[portIndex]->isEmpty()) {
            AgentPacket *pkt = check_and_cast<AgentPacket *>(txQueues[portIndex]->pop());
            cChannel *channel = gate("port$o", portIndex)->getTransmissionChannel();
            cDelayChannel *delayChannel = dynamic_cast<cDelayChannel*>(channel);
            if (delayChannel) {
                double baseDelay = baseChannelDelays[portIndex];
                double noise = (baseDelay > 0.0015) ? uniform(0, baseDelay * 0.25) : 0.0;
                delayChannel->setDelay(std::max(0.0001, baseDelay + noise));
            }
            send(pkt, "port$o", portIndex); 
            scheduleAt(channel->getTransmissionFinishTime(), endTxMsgs[portIndex]);
        }
        return; 
    }

    if (msg->isPacket()) {
        AgentPacket *pkt = check_and_cast<AgentPacket *>(msg);
        if (std::string(pkt->getDestAgent()) == myAgentId) {
            
            std::string srcId = pkt->getSrcAgent();
            
            // ==============================================================
            // FÍSICA DE RECEPTOR: Rola os dados para ver se o pacote sobreviveu!
            // ==============================================================
            if (uniform(0, 1) < inDropChances[srcId]) {
                par("packets_dropped") = par("packets_dropped").doubleValue() + 1;
                delete pkt; 
                return; // Morreu na praia!
            }

            double latency = (simTime() - pkt->getCreationTime()).dbl();
            double size = pkt->getByteLength();
            double previous_latency = lastLatencies[srcId];
            double jitter = (previous_latency > 0) ? std::abs(latency - previous_latency) : 0.0;
            
            par("packets_received") = par("packets_received").doubleValue() + 1;
            lastLatencies[srcId] = latency; 
            
            std::string payload = pkt->getPayload();
            std::string current_out = par("val_out").stdstringValue();
            par("val_out").setStringValue(current_out.empty() ? payload.c_str() : (current_out + "|||" + payload).c_str());
            
            std::string cur_sizes = par("packet_sizes_out").stdstringValue();
            std::string cur_lats = par("latencies_out").stdstringValue();
            std::string cur_jits = par("jitters_out").stdstringValue();

            par("packet_sizes_out").setStringValue(cur_sizes.empty() ? std::to_string(size).c_str() : (cur_sizes + "|||" + std::to_string(size)).c_str());
            par("latencies_out").setStringValue(cur_lats.empty() ? std::to_string(latency).c_str() : (cur_lats + "|||" + std::to_string(latency)).c_str());
            par("jitters_out").setStringValue(cur_jits.empty() ? std::to_string(jitter).c_str() : (cur_jits + "|||" + std::to_string(jitter)).c_str());
            
            delete pkt;
        } else {
            delete pkt; 
        }
    } else {
        delete msg;
    }
}

std::vector<std::string> AgentNode::splitString(const std::string& s, const std::string& delimiter) {
    size_t pos_start = 0, pos_end, delim_len = delimiter.length();
    std::string token;
    std::vector<std::string> res;
    while ((pos_end = s.find(delimiter, pos_start)) != std::string::npos) {
        token = s.substr(pos_start, pos_end - pos_start);
        pos_start = pos_end + delim_len;
        if (!token.empty()) res.push_back(token);
    }
    res.push_back(s.substr(pos_start));
    return res;
}