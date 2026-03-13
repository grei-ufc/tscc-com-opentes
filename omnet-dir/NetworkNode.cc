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

void NetworkNode::handleMessage(cMessage *msg) {
    
    // Se a mensagem for o nosso relógio interno (timer)
    if (msg == timerEvent) {
        
        // 1. Lê a variável que o Mosaik (através do Bridge) pode ter alterado
        double currentDataIn = par("data_in").doubleValue();

        if (currentDataIn > 0) {
            EV << "NetworkNode " << getName() << ": O Mosaik mandou " << currentDataIn 
               << ". A gerar pacote de rede!" << std::endl;

            // 2. Cria um pacote de rede genuíno do OMNeT++
            char msgName[32];
            sprintf(msgName, "Pacote_Mosaik-%d", ++packetCounter);
            cMessage *pkt = new cMessage(msgName);

            // 3. Atualiza a estatística de saída (o Bridge lerá isto no próximo 'step')
            double currentDataOut = par("data_out").doubleValue();
            par("data_out").setDoubleValue(currentDataOut + 1.0); // Incrementa contador de envio

            // 4. "Consome" a instrução do Mosaik para não disparar em loop infinito
            par("data_in").setDoubleValue(0.0);

            // 5. Tenta enviar o pacote pela primeira porta do vetor "out[]"
            if (gateSize("out") > 0 && gate("out", 0)->isConnected()) {
                send(pkt, "out", 0); // O '0' indica o índice do vetor da porta
                EV << "NetworkNode " << getName() << ": Pacote enviado com sucesso!" << std::endl;
            } else {
                EV << "NetworkNode " << getName() << ": Nenhuma porta conectada. Pacote descartado." << std::endl;
                delete pkt; 
            }
        }
        // Reagenda o relógio para verificar novamente daqui a 1 segundo de simulação
        scheduleAt(simTime() + 1.0, timerEvent);
        
    } 
    // Se a mensagem não for o timer, significa que é um pacote a chegar de OUTRO nó
    else {
        EV << "NetworkNode " << getName() << ": Recebi o pacote " 
           << msg->getName() << " vindo da rede!" << std::endl;
        
        // Destrói o pacote após o processar (evita fugas de memória)
        delete msg;
    }
}

void NetworkNode::finish() {
    // Limpeza padrão
    if (timerEvent) {
        cancelAndDelete(timerEvent);
    }
}
