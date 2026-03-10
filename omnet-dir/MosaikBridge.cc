#include <omnetpp.h>
#include <zmq.hpp>
#include <nlohmann/json.hpp>
#include <string>

using namespace omnetpp;
using json = nlohmann::json;

class MosaikBridge : public cSimpleModule {
  private:
    zmq::context_t context{1};
    zmq::socket_t socket{context, zmq::socket_type::rep};
    cMessage *stepMsg = nullptr;

  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
};

Define_Module(MosaikBridge);

void MosaikBridge::initialize() {
    socket.bind("tcp://*:5555");
    EV << "MosaikBridge: Aguardando conexao do mosaik na porta 5555..." << std::endl;

    bool scenario_ready = false;
    
    while (!scenario_ready) {
        zmq::message_t request;
        socket.recv(request, zmq::recv_flags::none);
        
        std::string msg_str(static_cast<char*>(request.data()), request.size());
        json j = json::parse(msg_str);

        EV << "\n>>> RECEBIDO DO MOSAIK (SETUP):\n" << j.dump(4) << "\n" << std::endl;

        // --- CRIAR NÓ ---
        if (j["action"] == "create") {
            std::string modelName = j["params"]["node_type"];
            std::string entityId = j["eid"];

            cModuleType *moduleType = cModuleType::find(modelName.c_str());
            json response;

            if (moduleType) {
                cModule *newModule = moduleType->create(entityId.c_str(), getParentModule());
                newModule->finalizeParameters();
                newModule->buildInside();
                newModule->scheduleStart(simTime());
                
                EV << "MosaikBridge: Modulo " << entityId << " criado com sucesso." << std::endl;
                response = {{"status", "ok"}};
            } else {
                EV_ERROR << "MosaikBridge: Tipo de modulo nao encontrado: " << modelName << std::endl;
                response = {{"status", "error", "reason", "Tipo de modulo nao encontrado"}};
            }

            EV << "<<< ENVIANDO PARA O MOSAIK:\n" << response.dump(4) << "\n" << std::endl;
            socket.send(zmq::buffer(response.dump()), zmq::send_flags::none);
        } 
        // --- CRIAR CONEXÃO (CABO) ---
        else if (j["action"] == "connect") {
            std::string srcId = j["src"];
            std::string destId = j["dest"];

            cModule *srcNode = getParentModule()->getSubmodule(srcId.c_str());
            cModule *destNode = getParentModule()->getSubmodule(destId.c_str());
            json response;

            if (srcNode && destNode) {
                // Aumenta o tamanho do vetor das portas "out" na origem e "in" no destino
                srcNode->setGateSize("out", srcNode->gateSize("out") + 1);
                destNode->setGateSize("in", destNode->gateSize("in") + 1);

                // Pega a referência para as portas recém-criadas (último índice)
                cGate *srcGate = srcNode->gate("out", srcNode->gateSize("out") - 1);
                cGate *destGate = destNode->gate("in", destNode->gateSize("in") - 1);

                // Cria o canal e liga
                cIdealChannel *channel = cIdealChannel::create("channel");
                srcGate->connectTo(destGate, channel);
                
                // Ligar o canal na memória (Obrigatório para canais dinâmicos)
                channel->callInitialize();

                EV << "MosaikBridge: Conectado cabo de " << srcId << " para " << destId << std::endl;
                response = {{"status", "ok"}};
            } else {
                EV_ERROR << "MosaikBridge: Erro ao conectar. Nó não encontrado." << std::endl;
                response = {{"status", "error", "reason", "Nó de origem ou destino não encontrado"}};
            }

            EV << "<<< ENVIANDO PARA O MOSAIK:\n" << response.dump(4) << "\n" << std::endl;
            socket.send(zmq::buffer(response.dump()), zmq::send_flags::none);
        }
        // --- INICIAR SIMULAÇÃO ---
        else if (j["action"] == "step") {
            scenario_ready = true;
            stepMsg = new cMessage("next_step");
            
            double stepSize = 1.0; 
            scheduleAt(simTime() + stepSize, stepMsg);
            
            EV << "MosaikBridge: Cenario montado. Iniciando loop de simulacao..." << std::endl;
        }
    }
}

void MosaikBridge::handleMessage(cMessage *msg) {
    if (msg == stepMsg) {
        
        // 1. EXTRAÇÃO DE DADOS DOS NÓS
        json data_json = json::object();

        for (cModule::SubmoduleIterator it(getParentModule()); !it.end(); ++it) {
            cModule *submod = *it;
            if (submod == this) continue; 

            std::string nodeName = submod->getName();
            json node_data = json::object();

            if (submod->hasPar("status")) {
                node_data["status"] = submod->par("status").stdstringValue();
            } else {
                node_data["status"] = "unknown";
            }

            if (submod->hasPar("data_out")) {
                node_data["data_out"] = submod->par("data_out").doubleValue();
            } else {
                node_data["data_out"] = 0.0;
            }

            data_json[nodeName] = node_data;
        }

        json response = {
            {"status", "ok"},
            {"data", data_json}
        };
        
        EV << "\n<<< ENVIANDO RESULTADOS PARA O MOSAIK:\n" << response.dump(4) << "\n" << std::endl;
        socket.send(zmq::buffer(response.dump()), zmq::send_flags::none);

        // 2. RECEBE PRÓXIMO COMANDO DO MOSAIK
        zmq::message_t next_request;
        socket.recv(next_request, zmq::recv_flags::none);
        
        std::string msg_str(static_cast<char*>(next_request.data()), next_request.size());
        json j = json::parse(msg_str);

        EV << "\n>>> RECEBIDO DO MOSAIK (PASSO):\n" << j.dump(4) << "\n" << std::endl;

        // 3. APLICA INPUTS E AVANÇA O TEMPO
        if (j["action"] == "step") {
            
            if (j.contains("inputs") && !j["inputs"].is_null()) {
                json inputs = j["inputs"];
                
                for (auto& [nodeName, nodeAttributes] : inputs.items()) {
                    cModule *targetNode = getParentModule()->getSubmodule(nodeName.c_str());
                    
                    if (targetNode != nullptr) {
                        for (auto& [attrName, sources] : nodeAttributes.items()) {
                            
                            double totalValue = 0.0;
                            for (auto& [sourceEntity, value] : sources.items()) {
                                totalValue += value.get<double>();
                            }
                            
                            if (targetNode->hasPar(attrName.c_str())) {
                                targetNode->par(attrName.c_str()).setDoubleValue(totalValue);
                                EV << "MosaikBridge: Injetado no nó " << nodeName 
                                   << " atributo " << attrName << " = " << totalValue << std::endl;
                            }
                        }
                    }
                }
            }

            double stepSize = 1.0;
            scheduleAt(simTime() + stepSize, stepMsg);
            
        } else if (j["action"] == "stop") {
            endSimulation();
        }
    } else {
        delete msg; 
    }
}

void MosaikBridge::finish() {
    if (stepMsg) {
        cancelAndDelete(stepMsg);
    }
    socket.close();
    EV << "MosaikBridge: Conexao encerrada e memoria limpa." << std::endl;
}