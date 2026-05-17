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
        
        // Calcula o jitter baseado na última latência conhecida
        double previous_latency = par("last_latency").doubleValue();
        double jitter = (previous_latency > 0) ? std::abs(latency - previous_latency) : 0.0;
        
        par("packets_received") = par("packets_received").doubleValue() + 1;
        par("last_latency") = latency; // Mantemos isto apenas para o cálculo interno do Jitter no próximo pacote
        
        // MULTIPLEXAGEM DE SAÍDA (Mensagens FIPA)
        std::string payload = pkt->getName();
        std::string current_out = par("val_out").stdstringValue();
        if (current_out.empty()) {
            par("val_out").setStringValue(payload.c_str());
        } else {
            par("val_out").setStringValue((current_out + "|||" + payload).c_str());
        }
        
        // ==============================================================
        // MULTIPLEXAGEM DE TELEMETRIA (Para evitar aliasing no Gráfico)
        // ==============================================================
        std::string cur_sizes = par("packet_sizes_out").stdstringValue();
        std::string cur_lats = par("latencies_out").stdstringValue();
        std::string cur_jits = par("jitters_out").stdstringValue();

        std::string new_size = std::to_string(size);
        std::string new_lat = std::to_string(latency);
        std::string new_jit = std::to_string(jitter);

        par("packet_sizes_out").setStringValue(cur_sizes.empty() ? new_size.c_str() : (cur_sizes + "|||" + new_size).c_str());
        par("latencies_out").setStringValue(cur_lats.empty() ? new_lat.c_str() : (cur_lats + "|||" + new_lat).c_str());
        par("jitters_out").setStringValue(cur_jits.empty() ? new_jit.c_str() : (cur_jits + "|||" + new_jit).c_str());
        
        EV << "[OMNeT++] Pacote de " << size << " bytes ENTREGUE. Latencia: " << latency << "s" << std::endl;
        delete pkt;
        return;
    }

    // ==============================================================
    // 2. VERIFICA SE O MOSAIK INJETOU ALGO NOVO (MULTIPLEXAGEM DE ENTRADA)
    // ==============================================================
    std::string current_in = par("val_in").stdstringValue();
    
    if (!current_in.empty()) {
        std::vector<std::string> messages;
        size_t pos = 0;
        std::string delimiter = "|||";
        
        // Separa o comboio de mensagens num Array
        while ((pos = current_in.find(delimiter)) != std::string::npos) {
            messages.push_back(current_in.substr(0, pos));
            current_in.erase(0, pos + delimiter.length());
        }
        messages.push_back(current_in); // Adiciona a última

        // Processa cada mensagem de forma independente
        for (const std::string& msg_str : messages) {
            if (msg_str.empty()) continue;

            double drop_prob = par("drop_probability").doubleValue();
            if (uniform(0.0, 1.0) < drop_prob) {
                EV << "[OMNeT++] ❌ DROP! Pacote FIPA descartado." << std::endl;
                par("packets_dropped") = par("packets_dropped").doubleValue() + 1;
                continue; 
            }

            cPacket *pkt = new cPacket(msg_str.c_str());
            pkt->setByteLength(msg_str.length()); 
            
            double propagation_delay = 0.010; 
            double bandwidth_bps = par("bandwidth_bps").doubleValue();   
            double bits = msg_str.length() * 8.0;
            double transmission_delay = bits / bandwidth_bps;
            double jitter_mean = par("jitter_mean").doubleValue();
            double stochastic_delay = (jitter_mean > 0.0) ? exponential(jitter_mean) : 0.0;
            
            double total_latency = propagation_delay + transmission_delay + stochastic_delay;

            scheduleAt(simTime() + total_latency, pkt); 
            par("packets_sent") = par("packets_sent").doubleValue() + 1;
        }
        par("val_in").setStringValue(""); // Limpa o buffer
    }
    
    if (!msg->isPacket()) {
        scheduleAt(simTime() + 1.0, msg);
    }
}