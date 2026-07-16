/**
 * @file AgentNode.cc
 * @brief Nó de rede descentralizado com Fila de Buffers, Rastreamento de Jitter 
 * por Origem e Simulação de Ruído Estocástico (Wireless Air Fluctuation).
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
    
    // Dicionário para rastrear a última latência de cada remetente!
    std::map<std::string, double> lastLatencies;

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
    // O nó agora descobre seu próprio nome automaticamente!
    myAgentId = getName(); 
    EV << "AgentNode " << myAgentId << " inicializado." << std::endl;

    int numPorts = gateSize("port");
    for (int i = 0; i < numPorts; i++) {
        txQueues[i] = new cPacketQueue(("txQueue_" + std::to_string(i)).c_str());
        
        cMessage *endTxMsg = new cMessage(("endTx_" + std::to_string(i)).c_str());
        endTxMsg->setContextPointer((void *)(intptr_t)i); 
        endTxMsgs[i] = endTxMsg;

        cGate *outGate = gate("port$o", i);
        if (outGate->getPathEndGate() != nullptr) {
            cModule *neighbor = outGate->getPathEndGate()->getOwnerModule();
            
            // Mapeia a porta usando o nome dinâmico do vizinho
            std::string neighborId = neighbor->getName();
            routingTable[neighborId] = i; 
        }
    }
}

AgentNode::~AgentNode() {
    // Corrigido para C++ clássico (evita warnings do C++17)
    for (auto const& pair : txQueues) delete pair.second;
    for (auto const& pair : endTxMsgs) cancelAndDelete(pair.second);
}

void AgentNode::handleParameterChange(const char *parname)
{
    if (std::string(parname) == "val_in") {
        if (!std::string(par("val_in").stdstringValue()).empty()) {
            processInjectedData();
        }
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
        send(pkt, "port$o", portIndex); 
        
        // ==============================================================
        // CORREÇÃO: Cast seguro para extrair o Delay do Canal
        // ==============================================================
        cDelayChannel *delayChannel = dynamic_cast<cDelayChannel*>(channel);
        double baseDelay = delayChannel ? delayChannel->getDelay().dbl() : 0.0;
        
        double stochasticNoise = 0.0;
        if (baseDelay > 0.0015) { 
            stochasticNoise = std::abs(normal(0.0, baseDelay * 0.25)); 
        }
        
        simtime_t finishTime = channel->getTransmissionFinishTime() + SimTime(stochasticNoise);
        scheduleAt(finishTime, endTxMsgs[portIndex]);
    } else {
        txQueues[portIndex]->insert(pkt);
    }
}

void AgentNode::processInjectedData()
{
    std::string current_in = par("val_in").stdstringValue();
    if (current_in.empty()) return;

    par("val_in").setStringValue(""); 

    std::vector<std::string> messages = splitString(current_in, "|||");

    for (const std::string& msg_str : messages) {
        if (msg_str.empty()) continue;

        try {
            json jMsg = json::parse(msg_str);
            std::vector<std::string> destIds;

            if (jMsg.contains("receivers") && jMsg["receivers"].is_array()) {
                for (auto& rec : jMsg["receivers"]) {
                    std::string rawReceiver = rec.get<std::string>();
                    size_t atPos = rawReceiver.find('@');
                    std::string padeId = (atPos != std::string::npos) ? rawReceiver.substr(0, atPos) : rawReceiver;
                    
                    std::string omnetId = mapPadeToOmnet(padeId);
                    if (!omnetId.empty()) destIds.push_back(omnetId);
                }
            }

            if (destIds.empty()) continue;

            for (const std::string& destId : destIds) {
                if (routingTable.find(destId) != routingTable.end()) {
                    int portIndex = routingTable[destId];

                    AgentPacket *pkt = new AgentPacket(msg_str.c_str());
                    pkt->setSrcAgent(myAgentId.c_str());
                    pkt->setDestAgent(destId.c_str());
                    pkt->setPayload(msg_str.c_str()); 
                    pkt->setByteLength(msg_str.length());

                    transmitPacket(pkt, portIndex);
                    par("packets_sent") = par("packets_sent").doubleValue() + 1;
                } else {
                    par("packets_dropped") = par("packets_dropped").doubleValue() + 1;
                }
            }
        } catch (json::parse_error& e) {
            EV << "Erro JSON no AgentNode " << myAgentId << ": " << e.what() << '\n';
        }
    }
}

void AgentNode::handleMessage(cMessage *msg)
{
    if (msg->isSelfMessage()) {
        int portIndex = (int)(intptr_t)msg->getContextPointer();
        if (!txQueues[portIndex]->isEmpty()) {
            AgentPacket *pkt = check_and_cast<AgentPacket *>(txQueues[portIndex]->pop());
            send(pkt, "port$o", portIndex); 
            
            cChannel *channel = gate("port$o", portIndex)->getTransmissionChannel();
            
            // ==============================================================
            // CORREÇÃO: Cast seguro para os pacotes saindo da fila
            // ==============================================================
            cDelayChannel *delayChannel = dynamic_cast<cDelayChannel*>(channel);
            double baseDelay = delayChannel ? delayChannel->getDelay().dbl() : 0.0;
            
            double stochasticNoise = (baseDelay > 0.0015) ? std::abs(normal(0.0, baseDelay * 0.25)) : 0.0;

            scheduleAt(channel->getTransmissionFinishTime() + SimTime(stochasticNoise), endTxMsgs[portIndex]);
        }
        return; 
    }

    if (msg->isPacket()) {
        AgentPacket *pkt = check_and_cast<AgentPacket *>(msg);
        
        if (std::string(pkt->getDestAgent()) == myAgentId) {
            
            double latency = (simTime() - pkt->getCreationTime()).dbl();
            double size = pkt->getByteLength();
            
            std::string srcId = pkt->getSrcAgent();
            double previous_latency = lastLatencies[srcId];
            double jitter = (previous_latency > 0) ? std::abs(latency - previous_latency) : 0.0;
            
            par("packets_received") = par("packets_received").doubleValue() + 1;
            lastLatencies[srcId] = latency; 
            
            std::string payload = pkt->getPayload();
            std::string current_out = par("val_out").stdstringValue();
            if (current_out.empty()) {
                par("val_out").setStringValue(payload.c_str());
            } else {
                par("val_out").setStringValue((current_out + "|||" + payload).c_str());
            }
            
            std::string cur_sizes = par("packet_sizes_out").stdstringValue();
            std::string cur_lats = par("latencies_out").stdstringValue();
            std::string cur_jits = par("jitters_out").stdstringValue();

            std::string new_size = std::to_string(size);
            std::string new_lat = std::to_string(latency);
            std::string new_jit = std::to_string(jitter);

            par("packet_sizes_out").setStringValue(cur_sizes.empty() ? new_size.c_str() : (cur_sizes + "|||" + new_size).c_str());
            par("latencies_out").setStringValue(cur_lats.empty() ? new_lat.c_str() : (cur_lats + "|||" + new_lat).c_str());
            par("jitters_out").setStringValue(cur_jits.empty() ? new_jit.c_str() : (cur_jits + "|||" + new_jit).c_str());
            
            EV << "[OMNeT++] Pacote de " << srcId << " ENTREGUE a " << myAgentId 
               << ". Latencia: " << latency << "s | Jitter: " << jitter << "s\n";
            
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
    std::string lastToken = s.substr(pos_start);
    if (!lastToken.empty()) res.push_back(lastToken);
    return res;
}