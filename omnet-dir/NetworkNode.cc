/**
 * @file NetworkNode.cc
 * @brief Implementação da lógica comportamental do NetworkNode.
 */

#include <omnetpp.h>

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
    EV << "NetworkNode " << getName() << " inicializado." << std::endl;
    // Dispara o primeiro pulso
    cMessage *wakeUpMsg = new cMessage("wakeup");
    scheduleAt(simTime(), wakeUpMsg);
}

void NetworkNode::handleMessage(cMessage *msg)
{
    // SE FOR UMA MENSAGEM RECEBIDA DE OUTRO NÓ PELA REDE
    if (msg->isPacket()) {
        cPacket *pkt = check_and_cast<cPacket *>(msg);
        
        double latency = (simTime() - pkt->getCreationTime()).dbl();
        double size = pkt->getByteLength();
        
        par("packets_received") = par("packets_received").doubleValue() + 1;
        par("last_latency") = latency;
        par("last_packet_size") = size;
        
        EV << "NetworkNode " << getName() << " RECEBEU pacote. Latencia: " << latency << "s" << std::endl;
           
        delete pkt;
        return;
    }

    // SE FOR O PULSO INTERNO, VERIFICA SE O MOSAIK INJETOU ALGO
    double current_in = par("data_in").doubleValue();
    
    if (current_in > 0) {
        EV << "NetworkNode " << getName() << ": Injetando trafego! Fazendo BROADCAST..." << std::endl;
        
        int numGates = gateSize("out");
        int pacotesEnviadosNesteCiclo = 0;
        
        for (int i = 0; i < numGates; i++) {
            cGate *outGate = gate("out", i);
            
            if (outGate != nullptr && outGate->isConnected()) {
                cPacket *pkt = new cPacket("Pacote_Mosaik_Broadcast");
                pkt->setByteLength(1024); 
                send(pkt, outGate);
                pacotesEnviadosNesteCiclo++;
            }
        }
        
        if (pacotesEnviadosNesteCiclo > 0) {
            par("packets_sent") = par("packets_sent").doubleValue() + pacotesEnviadosNesteCiclo;
            par("data_out") = par("packets_sent").doubleValue();
        }
        
        par("data_in") = 0.0;
    }
    
    // Reagenda o pulso para o próximo segundo
    if (!msg->isPacket()) {
        scheduleAt(simTime() + 1.0, msg);
    }
}