/**
 * @file MosaikBridge.cc
 * @brief Ponte de comunicação entre OMNeT++ e Mosaik via ZeroMQ.
 *
 * PROTOCOLO CÍCLICO (REQ-REP correto):
 *
 *  SETUP (initialize):
 *    Mosaik SEND(CREATE/CONNECT) → OMNeT++ processa → SEND(ACK)
 *    Mosaik SEND(STEP t=0, inputs) → OMNeT++ aplica inputs
 *                                   → SEND(dados_iniciais)   ← CORRIGIDO
 *                                   → agenda evento interno
 *
 *  LOOP (handleMessage):
 *    [OMNeT++ avança internamente]
 *    handleMessage dispara
 *    OMNeT++ RECV(STEP t+1, inputs)  ← bloqueia até Mosaik enviar
 *    OMNeT++ aplica inputs → coleta dados
 *    OMNeT++ SEND(dados_t+1)
 *    [repete]
 */

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

    // Rastreia o passo atual do Mosaik
    int mosaik_step = 0;
    double time_resolution = 1.0;  // segundos por passo (recebido do Mosaik)

  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

  private:
    // Extrai os dados de todos os nós filhos e retorna JSON
    json collectNodeData();

    // Aplica o dict de inputs do Mosaik nos parâmetros dos módulos
    void applyInputs(const json &inputs);
};

Define_Module(MosaikBridge);

// ---------------------------------------------------------------------------
// Utilitários privados
// ---------------------------------------------------------------------------

json MosaikBridge::collectNodeData() {
    json data = json::object();
    for (cModule::SubmoduleIterator it(getParentModule()); !it.end(); ++it) {
        cModule *submod = *it;
        if (submod == this) continue;

        std::string name = submod->getName();
        json node;

        node["status"]   = submod->hasPar("status")   ? submod->par("status").stdstringValue() : "idle";
        node["data_out"] = submod->hasPar("data_out")  ? submod->par("data_out").doubleValue()  : 0.0;

        if (submod->hasPar("packets_sent"))     node["packets_sent"]     = submod->par("packets_sent").doubleValue();
        if (submod->hasPar("packets_received")) node["packets_received"] = submod->par("packets_received").doubleValue();
        if (submod->hasPar("last_latency"))     node["last_latency"]     = submod->par("last_latency").doubleValue();
        if (submod->hasPar("last_packet_size")) node["last_packet_size"] = submod->par("last_packet_size").doubleValue();

        data[name] = node;
    }
    return data;
}

void MosaikBridge::applyInputs(const json &inputs) {
    if (inputs.is_null() || !inputs.is_object()) return;

    for (auto& [nodeName, nodeAttributes] : inputs.items()) {
        cModule *target = getParentModule()->getSubmodule(nodeName.c_str());
        if (!target) {
            EV_WARN << "MosaikBridge: nó alvo não encontrado: " << nodeName << std::endl;
            continue;
        }
        for (auto& [attrName, sources] : nodeAttributes.items()) {
            double total = 0.0;
            for (auto& [src, val] : sources.items()) {
                total += val.get<double>();
            }
            if (target->hasPar(attrName.c_str())) {
                target->par(attrName.c_str()).setDoubleValue(total);
                EV << "MosaikBridge: injetado " << nodeName << "." << attrName
                   << " = " << total << std::endl;
            }
        }
    }
}

// ---------------------------------------------------------------------------
// initialize: fase de setup — CREATE / CONNECT / primeiro STEP
// ---------------------------------------------------------------------------

void MosaikBridge::initialize() {
    socket.bind("tcp://*:5555");
    EV << "MosaikBridge: aguardando Mosaik na porta 5555..." << std::endl;

    while (true) {
        // REP: sempre RECV primeiro
        zmq::message_t request;
        socket.recv(request, zmq::recv_flags::none);

        std::string raw(static_cast<char*>(request.data()), request.size());
        json j = json::parse(raw);
        EV << "\n>>> SETUP RECV:\n" << j.dump(4) << "\n" << std::endl;

        // ---- CREATE ----
        if (j["action"] == "create") {
            std::string modelName = j["params"]["node_type"];
            std::string eid       = j["eid"];

            cModuleType *type = cModuleType::find(modelName.c_str());
            json resp;
            if (type) {
                cModule *m = type->create(eid.c_str(), getParentModule());
                m->finalizeParameters();
                m->buildInside();
                m->scheduleStart(simTime());
                resp = {{"status", "ok"}};
            } else {
                resp = {{"status", "error"}, {"reason", "tipo de módulo não encontrado"}};
            }
            EV << "<<< SETUP SEND:\n" << resp.dump(4) << "\n" << std::endl;
            socket.send(zmq::buffer(resp.dump()), zmq::send_flags::none);

        // ---- CONNECT ----
        } else if (j["action"] == "connect") {
            std::string srcId  = j["src"];
            std::string destId = j["dest"];

            cModule *src  = getParentModule()->getSubmodule(srcId.c_str());
            cModule *dest = getParentModule()->getSubmodule(destId.c_str());
            json resp;

            if (src && dest) {
                src->setGateSize("out",  src->gateSize("out")  + 1);
                dest->setGateSize("in", dest->gateSize("in")  + 1);

                cGate *gSrc  = src->gate("out",  src->gateSize("out")  - 1);
                cGate *gDest = dest->gate("in", dest->gateSize("in")  - 1);

                cDatarateChannel *ch = cDatarateChannel::create("channel");
                ch->setDelay(0.015);        // 15 ms latência
                ch->setDatarate(1000000);   // 1 Mbps
                ch->setPacketErrorRate(0.10); // 10 % PER
                gSrc->connectTo(gDest, ch);
                ch->callInitialize();

                resp = {{"status", "ok"}};
            } else {
                resp = {{"status", "error"}, {"reason", "nó de origem ou destino não encontrado"}};
            }
            EV << "<<< SETUP SEND:\n" << resp.dump(4) << "\n" << std::endl;
            socket.send(zmq::buffer(resp.dump()), zmq::send_flags::none);

        // ---- PRIMEIRO STEP — inicia o loop ----
        // CORREÇÃO PRINCIPAL: agora responde com os dados iniciais antes de
        // entrar no loop de eventos, desbloquando o recv_json() do wrapper.
        } else if (j["action"] == "step") {

            // Captura o time_resolution enviado pelo wrapper (se presente)
            if (j.contains("time_resolution")) {
                time_resolution = j["time_resolution"].get<double>();
            }
            mosaik_step = j.value("time", 0);

            EV << "MosaikBridge: primeiro STEP recebido (t=" << mosaik_step
               << ", time_resolution=" << time_resolution << "s)" << std::endl;

            // Aplica os inputs iniciais (se houver)
            if (j.contains("inputs")) {
                applyInputs(j["inputs"]);
            }

            // Coleta o estado inicial dos nós
            json data = collectNodeData();

            // *** RESPONDE ao Mosaik — desbloqueia o recv_json() do wrapper ***
            json resp = {
                {"status",      "ok"},
                {"data",        data},
                {"mosaik_step", mosaik_step}
            };
            EV << "<<< PRIMEIRO STEP SEND (dados iniciais):\n" << resp.dump(4) << "\n" << std::endl;
            socket.send(zmq::buffer(resp.dump()), zmq::send_flags::none);

            // Agenda o primeiro evento interno (avança 1 passo no tempo do OMNeT++)
            stepMsg = new cMessage("next_step");
            scheduleAt(simTime() + time_resolution, stepMsg);

            EV << "MosaikBridge: setup concluído, entrando no loop de simulação." << std::endl;
            break;  // sai do while — handleMessage assume o controle
        }
    }
}

// ---------------------------------------------------------------------------
// handleMessage: loop principal — RECV → aplica → coleta → SEND → agenda
// ---------------------------------------------------------------------------

void MosaikBridge::handleMessage(cMessage *msg) {
    if (msg != stepMsg) {
        delete msg;
        return;
    }

    mosaik_step++;

    EV << "\n[handleMessage] passo interno OMNeT++ t=" << simTime()
       << " | aguardando STEP " << mosaik_step << " do Mosaik..." << std::endl;

    // 1. RECV — bloqueia até Mosaik enviar o próximo STEP
    //    (isso é a sincronização: OMNeT++ espera o Mosaik)
    zmq::message_t request;
    socket.recv(request, zmq::recv_flags::none);

    std::string raw(static_cast<char*>(request.data()), request.size());
    json j = json::parse(raw);
    EV << ">>> LOOP RECV (t=" << mosaik_step << "):\n" << j.dump(4) << "\n" << std::endl;

    if (j["action"] == "stop") {
        endSimulation();
        return;
    }

    if (j["action"] != "step") {
        // Mensagem inesperada — responde com erro e descarta
        json err = {{"status", "error"}, {"reason", "ação inesperada fora do loop de setup"}};
        socket.send(zmq::buffer(err.dump()), zmq::send_flags::none);
        scheduleAt(simTime() + time_resolution, stepMsg);
        return;
    }

    // Valida que o Mosaik e o OMNeT++ estão no mesmo passo (SYNC check)
    int mosaik_time_recv = j.value("time", -1);
    if (mosaik_time_recv != mosaik_step) {
        EV_WARN << "MosaikBridge: DESSINCRONIZAÇÃO! Esperava passo "
                << mosaik_step << " mas Mosaik enviou " << mosaik_time_recv << std::endl;
    }

    // 2. Aplica os inputs recebidos do Mosaik
    if (j.contains("inputs")) {
        applyInputs(j["inputs"]);
    }

    // 3. Coleta os dados atuais dos nós
    json data = collectNodeData();

    // 4. SEND — devolve resultados para o Mosaik
    json resp = {
        {"status",      "ok"},
        {"data",        data},
        {"mosaik_step", mosaik_step}
    };
    EV << "<<< LOOP SEND (t=" << mosaik_step << "):\n" << resp.dump(4) << "\n" << std::endl;
    socket.send(zmq::buffer(resp.dump()), zmq::send_flags::none);

    // 5. Agenda o próximo evento interno do OMNeT++
    scheduleAt(simTime() + time_resolution, stepMsg);
}

// ---------------------------------------------------------------------------
// finish
// ---------------------------------------------------------------------------

void MosaikBridge::finish() {
    if (stepMsg) {
        cancelAndDelete(stepMsg);
    }
    socket.close();
    EV << "MosaikBridge: conexão encerrada." << std::endl;
}