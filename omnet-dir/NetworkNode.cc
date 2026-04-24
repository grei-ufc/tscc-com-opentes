/**
 * @file NetworkNode.cc
 * @brief Nuvem de Rede: Recebe FIPA-ACL, aplica delay, e expõe para o destino.
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
        
        par("packets_received") = par("packets_received").doubleValue() + 1;
        par("last_latency") = latency;
        par("last_packet_size") = size;
        
        // Coloca a string FIPA-ACL na porta de saída para o Mosaik recolher!
        std::string payload = pkt->getName();
        par("val_out").setStringValue(payload.c_str());
        
        EV << "Nuvem OMNeT++ liberou pacote. Latencia: " << latency << "s" << std::endl;
           
        delete pkt;
        return;
    }

    // ==============================================================
    // 2. VERIFICA SE O MOSAIK INJETOU ALGO NOVO
    // ==============================================================
    std::string current_in = par("val_in").stdstringValue();
    
    if (!current_in.empty()) {
        EV << "Nuvem OMNeT++: Mensagem do PADE detectada! Simulando atraso..." << std::endl;
        
        cPacket *pkt = new cPacket(current_in.c_str());
        pkt->setByteLength(current_in.length()); 
        
        // A MAGIA: O nó agenda o pacote para chegar a si mesmo 15ms no futuro!
        scheduleAt(simTime() + 0.015, pkt); 
        
        par("packets_sent") = par("packets_sent").doubleValue() + 1;
        
        // Limpa a entrada para não gerar envios duplicados
        par("val_in").setStringValue("");
    }
    
    // Reagenda o pulso interno para continuar a escutar o Mosaik
    if (!msg->isPacket()) {
        scheduleAt(simTime() + 1.0, msg);
    }
}