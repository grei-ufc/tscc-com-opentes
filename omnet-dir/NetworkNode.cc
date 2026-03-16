/**
 * @file NetworkNode.cc
 * @brief Implementação da lógica comportamental do NetworkNode.
 *
 * Implementa as rotinas de inicialização (initialize) e tratamento de mensagens
 * (handleMessage) do nó da rede. Responsável por capturar o valor da variável
 * de entrada (@mutable data_in), gerar instâncias de pacotes e enviá-los via
 * canais dinâmicos alocados nas portas do vetor 'out[]'.
 */

#include <omnetpp.h>

using namespace omnetpp;

class NetworkNode : public cSimpleModule {
  private:
    cMessage *timerEvent = nullptr;
    int packetCounter = 0;

  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
};

Define_Module(NetworkNode);

void NetworkNode::initialize() {
    // Inicializa um relógio interno para o nó operar de forma independente
    // Agendamos o primeiro "tick" para 0.1s no futuro
    timerEvent = new cMessage("check_inputs");
    scheduleAt(simTime() + 0.1, timerEvent);
}

void NetworkNode::handleMessage(cMessage *msg)
{
    // SE FOR UMA MENSAGEM RECEBIDA DE OUTRO NÓ PELA REDE
    if (msg->isPacket()) {
        cPacket *pkt = check_and_cast<cPacket *>(msg);
        
        // 1. Calcula a Latência (Tempo atual - Tempo em que o pacote foi criado)
        double latency = (simTime() - pkt->getCreationTime()).dbl();
        
        // 2. Lê o tamanho do pacote
        double size = pkt->getByteLength();
        
        // 3. Atualiza os contadores para o Python ler
        par("packets_received") = par("packets_received").doubleValue() + 1;
        par("last_latency") = latency;
        par("last_packet_size") = size;
        
        EV << "NetworkNode " << getName() << " RECEBEU pacote de " << size 
           << " bytes. Latencia: " << latency << "s" << std::endl;
           
        delete pkt;
        return;
    }

    // SE FOR O COMANDO DO MOSAIK (A INJEÇÃO DE DADOS)
    double current_in = par("data_in").doubleValue();
    
    if (current_in > 0) {
        EV << "NetworkNode " << getName() << ": O Mosaik injetou dados. A gerar pacote de rede real!" << std::endl;
        
        // Em vez de cMessage, usamos cPacket para ter tamanho em bytes
        cPacket *pkt = new cPacket("Pacote_Mosaik");
        pkt->setByteLength(1024); // Exemplo: Pacote de 1024 Bytes (1 KB)
        
        if (gateSize("out") > 0 && gate("out", 0)->isConnected()) {
            send(pkt, "out", 0);
            
            // Atualiza os contadores de envio
            par("packets_sent") = par("packets_sent").doubleValue() + 1;
            par("data_out") = par("packets_sent").doubleValue(); // Mantemos o data_out a crescer para legado
            
        } else {
            delete pkt; 
        }
        
        // Zera o input para não disparar em loop infinito
        par("data_in") = 0.0;
    }
    
    // Agenda a próxima checagem
    scheduleAt(simTime() + 1.0, msg);
}

void NetworkNode::finish() {
    // Limpeza padrão
    if (timerEvent) {
        cancelAndDelete(timerEvent);
    }
}
