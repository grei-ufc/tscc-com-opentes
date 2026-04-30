/**
 * @file NetworkNode.cc
 * @brief Nuvem de Rede: Recebe FIPA-ACL, aplica delay realista, e expõe para o destino.
 */

#include <omnetpp.h>
#include <string>

using namespace omnetpp;

class NetworkNode : public cSimpleModule
{
  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
};

Define_Module(NetworkNode);

void NetworkNode::initialize()
{
    EV << "Nuvem OMNeT++ inicializada." << std::endl;
    // Dispara o primeiro pulso de leitura
    cMessage *wakeUpMsg = new cMessage("wakeup");
    scheduleAt(simTime(), wakeUpMsg);
}

void NetworkNode::handleMessage(cMessage *msg)
{
    // ==============================================================
    // 1. O PACOTE ACABOU DE SAIR DO "TÚNEL DE LATÊNCIA"
    // ==============================================================
    if (msg->isPacket()) {
        cPacket *pkt = check_and_cast<cPacket *>(msg);
        
        double latency = (simTime() - pkt->getCreationTime()).dbl();
        double size = pkt->getByteLength();
        
        // --- Cálculo de Jitter ---
        double previous_latency = par("last_latency").doubleValue();
        // O Jitter é a diferença absoluta entre a latência atual e a anterior
        double jitter = (previous_latency > 0) ? std::abs(latency - previous_latency) : 0.0;
        
        // Atualiza as métricas expostas
        par("packets_received") = par("packets_received").doubleValue() + 1;
        par("last_latency") = latency;
        par("last_packet_size") = size;
        par("current_jitter") = jitter; // Exporta o jitter calculado
        
        // Coloca a string FIPA-ACL na porta de saída para o Mosaik recolher
        std::string payload = pkt->getName();
        par("val_out").setStringValue(payload.c_str());
        
        EV << "[OMNeT++] Pacote de " << size << " bytes ENTREGUE. Latencia: " << latency 
           << "s | Jitter: " << jitter << "s" << std::endl;
           
        delete pkt;
        return;
    }

    // ==============================================================
    // 2. VERIFICA SE O MOSAIK INJETOU ALGO NOVO
    // ==============================================================
    std::string current_in = par("val_in").stdstringValue();
    
    if (!current_in.empty()) {
        
        // --- 2.1. Implementação Probabilística de Perda de Pacotes ---
        double drop_prob = par("drop_probability").doubleValue();
        // Lança o "dado" entre 0 e 1 usando a distribuição Uniforme nativa do OMNeT++
        if (uniform(0.0, 1.0) < drop_prob) {
            EV << "[OMNeT++] ❌ DROP! Pacote FIPA descartado por probabilidade (" << (drop_prob * 100) << "%)." << std::endl;
            par("packets_dropped") = par("packets_dropped").doubleValue() + 1;
            par("val_in").setStringValue(""); // Limpa o buffer
            return; // Encerra a função sem agendar a entrega
        }

        cPacket *pkt = new cPacket(current_in.c_str());
        pkt->setByteLength(current_in.length()); 
        
        // --- 2.2. Matemática da Rede + Fator Estocástico ---
        double propagation_delay = 0.010; 
        double bandwidth_bps = par("bandwidth_bps").doubleValue();   
        
        double bits = current_in.length() * 8.0;
        double transmission_delay = bits / bandwidth_bps;
        
        // Adiciona um ruído probabilístico via Dist. Exponencial
        double jitter_mean = par("jitter_mean").doubleValue();
        double stochastic_delay = (jitter_mean > 0.0) ? exponential(jitter_mean) : 0.0;
        
        double total_latency = propagation_delay + transmission_delay + stochastic_delay;

        // O pacote chega no futuro
        scheduleAt(simTime() + total_latency, pkt); 
        
        par("packets_sent") = par("packets_sent").doubleValue() + 1;
        par("val_in").setStringValue("");
    }
    
    // Reagenda o pulso interno para continuar a escutar o Mosaik
    if (!msg->isPacket()) {
        scheduleAt(simTime() + 1.0, msg);
    }
}