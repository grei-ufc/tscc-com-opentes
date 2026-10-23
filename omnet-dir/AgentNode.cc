/**
 * @file AgentNode.cc
 * @brief Física de Redes Realista: Filas Finitas (Buffer Overflow), Atraso Espacial,
 * Jitter por Ruído e Perda de Pacotes no Receptor (PER do canal + atenuação por distância/BER).
 */

#include <omnetpp.h>
#include <map>
#include <deque>
#include <string>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <random>
#include <nlohmann/json.hpp>
#include "AgentPacket_m.h"

using namespace omnetpp;
using json = nlohmann::json;

class AgentNode : public cSimpleModule
{
  private:
    std::string myAgentId;
    // Destino -> índice da porta do PRÓXIMO SALTO (caminho mínimo em nº de saltos).
    // Inclui vizinhos diretos e, em topologias multi-salto (árvore, anel...), nós distantes.
    std::map<std::string, int> routingTable;
    // Porta -> id do vizinho direto naquela porta (identifica o salto anterior na chegada).
    std::map<int, std::string> portNeighbor;
    std::map<int, cPacketQueue*> txQueues;
    std::map<int, cMessage*> endTxMsgs;

    std::map<std::string, double> lastLatencies;
    std::map<int, double> baseChannelDelays;
    std::map<std::string, double> inDropChances;

    // Gerador de aleatoriedade (hardware ou semente determinística via RANDOM_SEED)
    std::mt19937 rng;
    std::uniform_real_distribution<double> dist_prob;

    static double getChannelDelay(cChannel *channel) {
        if (auto *dr = dynamic_cast<cDatarateChannel*>(channel)) return dr->getDelay().dbl();
        if (auto *dl = dynamic_cast<cDelayChannel*>(channel)) return dl->getDelay().dbl();
        if (channel && channel->hasPar("delay")) return channel->par("delay").doubleValue();
        return 0.0;
    }

    static void setChannelDelay(cChannel *channel, double delaySec) {
        if (auto *dr = dynamic_cast<cDatarateChannel*>(channel)) dr->setDelay(delaySec);
        else if (auto *dl = dynamic_cast<cDelayChannel*>(channel)) dl->setDelay(delaySec);
        else if (channel && channel->hasPar("delay")) channel->par("delay").setDoubleValue(delaySec);
    }

  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void handleParameterChange(const char *parname) override;
    virtual ~AgentNode();

    void processInjectedData();
    void buildRoutingTable();
    void transmitPacket(AgentPacket *pkt, int portIndex);
    std::vector<std::string> splitString(const std::string& s, const std::string& delimiter);
    std::string mapPadeToOmnet(const std::string& padeId);
};

Define_Module(AgentNode);

void AgentNode::initialize()
{
    myAgentId = getName();
    EV << "AgentNode " << myAgentId << " inicializado." << std::endl;

    const char *seedEnv = std::getenv("RANDOM_SEED");
    if (seedEnv != nullptr && std::strlen(seedEnv) > 0) {
        rng.seed(static_cast<unsigned int>(std::stoul(seedEnv)) + static_cast<unsigned int>(getId()));
    } else {
        std::random_device rd;
        rng.seed(rd());
    }
    dist_prob = std::uniform_real_distribution<double>(0.0, 1.0);

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
            portNeighbor[i] = neighborId;

            if (neighbor->hasPar("xPos") && neighbor->hasPar("yPos")) {
                double nX = neighbor->par("xPos").doubleValue();
                double nY = neighbor->par("yPos").doubleValue();
                double dist = std::sqrt(std::pow(nX - myX, 2) + std::pow(nY - myY, 2));

                cChannel *txChannel = outGate->getTransmissionChannel();
                if (txChannel) {
                    double currentDelay = getChannelDelay(txChannel);
                    double propagationDelay = dist * 0.00005;
                    baseChannelDelays[i] = currentDelay + propagationDelay;
                    setChannelDelay(txChannel, baseChannelDelays[i]);
                } else {
                    baseChannelDelays[i] = 0.0;
                }

                // Chance base de erro por atenuação espacial: ~1.5% a cada 100m.
                inDropChances[neighborId] = (dist / 100.0) * 0.015;
            }
        }
    }

    buildRoutingTable();
}

/**
 * Roteamento estático por caminho mínimo (BFS em nº de saltos) sobre o grafo
 * formado pelas portas dos AgentNodes. Para cada nó alcançável guarda a porta
 * DESTE nó que inicia o caminho. Com isso um pacote pode atravessar vários
 * nós (árvore, anel, ...) e não apenas chegar a vizinhos diretos. Empates são
 * resolvidos pela menor porta (determinístico).
 */
void AgentNode::buildRoutingTable() {
    std::map<cModule*, int> firstPort;
    std::deque<cModule*> fila;
    firstPort[this] = -1;
    fila.push_back(this);

    while (!fila.empty()) {
        cModule *cur = fila.front();
        fila.pop_front();
        int n = cur->gateSize("port");
        for (int p = 0; p < n; p++) {
            cGate *og = cur->gate("port$o", p);
            if (!og || !og->getPathEndGate()) continue;
            cModule *nb = og->getPathEndGate()->getOwnerModule();
            if (!nb || firstPort.count(nb)) continue;
            firstPort[nb] = (cur == this) ? p : firstPort[cur];
            fila.push_back(nb);
        }
    }

    for (auto const& kv : firstPort) {
        if (kv.first != this) routingTable[kv.first->getName()] = kv.second;
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
    return padeId;
}

void AgentNode::transmitPacket(AgentPacket *pkt, int portIndex) {
    cChannel *channel = gate("port$o", portIndex)->getTransmissionChannel();
    if (!channel->isBusy() && txQueues[portIndex]->isEmpty()) {
        if (channel) {
            double baseDelay = baseChannelDelays[portIndex];
            double noise = (baseDelay > 0.0015) ? dist_prob(rng) * baseDelay * 0.25 : 0.0;
            setChannelDelay(channel, std::max(0.0001, baseDelay + noise));
        }
        send(pkt, "port$o", portIndex);
        scheduleAt(channel->getTransmissionFinishTime(), endTxMsgs[portIndex]);
    } else {
        // FILA FINITA (BUFFER OVERFLOW): máximo de 5 pacotes enfileirados por porta
        if (txQueues[portIndex]->getLength() >= 5) {
            par("packets_dropped") = par("packets_dropped").doubleValue() + 1;
            delete pkt;
        } else {
            txQueues[portIndex]->insert(pkt);
        }
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
            if (channel) {
                double baseDelay = baseChannelDelays[portIndex];
                double noise = (baseDelay > 0.0015) ? dist_prob(rng) * baseDelay * 0.25 : 0.0;
                setChannelDelay(channel, std::max(0.0001, baseDelay + noise));
            }
            send(pkt, "port$o", portIndex);
            scheduleAt(channel->getTransmissionFinishTime(), endTxMsgs[portIndex]);
        }
        return;
    }

    if (msg->isPacket()) {
        AgentPacket *pkt = check_and_cast<AgentPacket *>(msg);
        std::string srcId = pkt->getSrcAgent();
        std::string destId = pkt->getDestAgent();
        double packetSize = pkt->getByteLength();

        // Salto anterior (vizinho que acabou de transmitir). Sem porta de chegada
        // conhecida, usa a origem do pacote (comportamento original de vizinho direto).
        std::string prevHop = srcId;
        if (cGate *arrival = pkt->getArrivalGate()) {
            auto it = portNeighbor.find(arrival->getIndex());
            if (it != portNeighbor.end()) prevHop = it->second;
        }

        // Perda POR SALTO: 1. erro do canal físico (PER de Profiles.ned via DatarateChannel);
        // 2. penalidade espacial (distância do salto anterior) escalonada pelo payload (BER).
        double sizeFactor = std::max(1.0, packetSize / 15000.0);
        double baseDropChance = inDropChances[prevHop];
        double finalDropChance = std::min(0.99, baseDropChance * sizeFactor);

        if (pkt->hasBitError() || dist_prob(rng) < finalDropChance) {
            par("packets_dropped") = par("packets_dropped").doubleValue() + 1;
            delete pkt;
            return;
        }

        // Pacote de passagem: encaminha ao próximo salto (ou descarta se não há rota).
        if (destId != myAgentId) {
            auto route = routingTable.find(destId);
            if (route == routingTable.end()) {
                par("packets_dropped") = par("packets_dropped").doubleValue() + 1;
                delete pkt;
                return;
            }
            par("packets_forwarded") = par("packets_forwarded").doubleValue() + 1;
            transmitPacket(pkt, route->second);
            return;
        }

        {
            double latency = (simTime() - pkt->getCreationTime()).dbl();
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

            par("packet_sizes_out").setStringValue(cur_sizes.empty() ? std::to_string(packetSize).c_str() : (cur_sizes + "|||" + std::to_string(packetSize)).c_str());
            par("latencies_out").setStringValue(cur_lats.empty() ? std::to_string(latency).c_str() : (cur_lats + "|||" + std::to_string(latency)).c_str());
            par("jitters_out").setStringValue(cur_jits.empty() ? std::to_string(jitter).c_str() : (cur_jits + "|||" + std::to_string(jitter)).c_str());

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