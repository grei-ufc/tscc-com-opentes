/**
 * @file ServidorConsulta.cc
 * @brief Modo de consulta por mensagem sobre a rede do TSCC (ver ServidorConsulta.h).
 *
 * Uma consulta por vez, como no servidor de rotas da tese: quem pergunta
 * primeiro é atendido primeiro, e o relógio simulado avança pelo atraso de cada
 * mensagem. Não há disputa entre mensagens de consultas diferentes.
 */
#include "ServidorConsulta.h"
#include "AgentPacket_m.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <deque>

using namespace omnetpp;
using json = nlohmann::json;

Define_Module(ServidorConsulta);

namespace {

std::string minusculas(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return std::tolower(c); });
    return s;
}

// Vizinho direto ligado à porta p de um AgentNode, ou nullptr.
cModule *vizinho(cModule *no, int p) {
    cGate *og = no->gate("port$o", p);
    if (!og || !og->getPathEndGate()) return nullptr;
    return og->getPathEndGate()->getOwnerModule();
}

}  // namespace

cModule *ServidorConsulta::resolver(const std::string& nome) {
    // O nome do módulo, ou o da posição no nodes_xy.csv do caso: "611" -> agent_611,
    // "DSO" -> agent_dso. É a regra com que cosim.ieee13 nomeia os nós.
    auto it = nos.find(nome);
    if (it != nos.end()) return it->second;
    it = nos.find("agent_" + minusculas(nome));
    return it != nos.end() ? it->second : nullptr;
}

void ServidorConsulta::initialize(int stage) {
    if (stage == 0) {
        fimMsg = new cMessage("fim_consulta");
        guardaMsg = new cMessage("guarda_consulta");
        return;
    }
    // Estágio 1: todos os AgentNodes já montaram as tabelas de rota no estágio 0.
    for (cModule::SubmoduleIterator it(getParentModule()); !it.end(); ++it) {
        cModule *m = *it;
        if (m != this && m->hasGate("consulta")) nos[m->getName()] = m;
    }

    const char *portaEnv = std::getenv("OMNET_PORT");
    std::string porta = (portaEnv && *portaEnv) ? portaEnv : std::to_string(par("porta").intValue());
    std::string endpoint = "tcp://*:" + porta;
    socket.bind(endpoint);

    json i = info();
    // O run.sh do OpenTES espera "] pronto" no log.
    std::printf("[TSCC] pronto: %d nos, %d enlaces, servidor de consulta em %s\n",
                i["nodes"].get<int>(), i["links"].get<int>(), endpoint.c_str());
    std::fflush(stdout);
    servir();
}

json ServidorConsulta::info() {
    // Enlaces e saltos pelo grafo de portas dos AgentNodes.
    int enlaces = 0;
    double somaPer = 0.0;
    std::map<cModule*, int> indice;
    std::vector<cModule*> lista;
    for (auto& kv : nos) { indice[kv.second] = lista.size(); lista.push_back(kv.second); }
    size_t n = lista.size();
    std::vector<std::vector<int>> adj(n);
    for (size_t a = 0; a < n; ++a) {
        cModule *no = lista[a];
        for (int p = 0; p < no->gateSize("port"); ++p) {
            cModule *nb = vizinho(no, p);
            if (!nb || !indice.count(nb)) continue;
            size_t b = indice[nb];
            adj[a].push_back(b);
            if (b <= a) continue;
            enlaces++;
            cChannel *c = no->gate("port$o", p)->getTransmissionChannel();
            if (c && c->hasPar("per_enlace")) somaPer += c->par("per_enlace").doubleValue();
            else if (c && c->hasPar("per")) somaPer += c->par("per").doubleValue();
        }
    }
    int semRota = 0, somaSaltos = 0, pares = 0;
    for (size_t s = 0; s < n; ++s) {
        std::vector<int> dist(n, -1);
        std::deque<size_t> fila{s};
        dist[s] = 0;
        while (!fila.empty()) {
            size_t u = fila.front(); fila.pop_front();
            for (int v : adj[u]) if (dist[v] < 0) { dist[v] = dist[u] + 1; fila.push_back(v); }
        }
        for (size_t d = 0; d < n; ++d) {
            if (d == s) continue;
            if (dist[d] < 0) semRota++;
            else { somaSaltos += dist[d]; pares++; }
        }
    }
    return {
        {"status", "ok"},
        {"nodes", (int)n},
        {"links", enlaces},
        {"mean_link_per", enlaces ? somaPer / enlaces : 0.0},
        {"mean_hops", pares ? (double)somaSaltos / pares : 0.0},
        {"unreachable_pairs", semRota},
    };
}

void ServidorConsulta::servir() {
    // Bloqueia até chegar um pedido. Pedidos que não geram pacote são respondidos
    // aqui mesmo; um "route" que gera pacote devolve o controle à simulação, e a
    // resposta sai quando o AgentNode avisar a entrega ou o descarte.
    while (true) {
        zmq::message_t req;
        if (!socket.recv(req, zmq::recv_flags::none)) continue;
        json j = json::parse(std::string(static_cast<char*>(req.data()), req.size()), nullptr, false);
        if (j.is_discarded()) {
            socket.send(zmq::buffer(json({{"status", "error"}}).dump()), zmq::send_flags::none);
            continue;
        }
        std::string acao = j.value("action", "route");
        if (acao == "route") {
            iniciar(j);
            if (emVoo) return;
            continue;
        }
        if (acao == "info") {
            socket.send(zmq::buffer(info().dump()), zmq::send_flags::none);
            continue;
        }
        if (acao == "stop") {
            socket.send(zmq::buffer(json({{"status", "ok"}}).dump()), zmq::send_flags::none);
            endSimulation();
        }
        socket.send(zmq::buffer(json({{"status", "error"}, {"reason", "acao desconhecida"}}).dump()),
                    zmq::send_flags::none);
    }
}

void ServidorConsulta::iniciar(const json& j) {
    std::string src = j.value("src", ""), dst = j.value("dst", "");
    bytes = j.value("bytes", 0L);
    saltos = 0;
    atraso = 0.0;
    perdido = false;
    enviado = false;

    cModule *origem = resolver(src), *destino = resolver(dst);
    if (!origem || !destino) {
        // Agente sem nó na topologia. Como no servidor da tese, entrega sem
        // atraso, mas o nome é avisado no log e marcado na resposta.
        for (const std::string& nome : {src, dst}) {
            if (!resolver(nome) && desconhecidos.insert(nome).second) {
                std::printf("[TSCC] AVISO: '%s' nao tem no na topologia; entregue sem atraso\n",
                            nome.c_str());
                std::fflush(stdout);
            }
        }
        responder(true);
        return;
    }
    if (origem == destino) {
        responder();
        return;
    }

    auto *pkt = new AgentPacket("consulta");
    pkt->setKind(KIND_CONSULTA);
    pkt->setSrcAgent(origem->getName());
    pkt->setDestAgent(destino->getName());
    pkt->setByteLength(std::max(1L, bytes));
    emVoo = true;
    enviado = true;
    inicio = simTime();
    scheduleAt(simTime() + par("guarda_s"), guardaMsg);
    sendDirect(pkt, origem, "consulta");
}

void ServidorConsulta::contarSalto() {
    Enter_Method_Silent();
    if (emVoo) saltos++;
}

void ServidorConsulta::concluir(bool foiPerdido) {
    Enter_Method_Silent();
    if (!emVoo) return;
    emVoo = false;
    perdido = foiPerdido;
    atraso = (simTime() - inicio).dbl();
    cancelEvent(guardaMsg);
    // A resposta sai de um evento próprio, no mesmo instante: o servidor volta a
    // bloquear à espera do próximo pedido fora da pilha de chamadas do AgentNode.
    if (!fimMsg->isScheduled()) scheduleAt(simTime(), fimMsg);
}

void ServidorConsulta::responder(bool desconhecido) {
    json r = {
        {"status", "ok"},
        {"dropped", perdido},
        {"delay", atraso},
        // Saltos percorridos: os encaminhamentos mais o último enlace.
        {"hops", enviado ? saltos + 1 : 0},
        {"frames", (int)std::max(1L, (bytes + 126) / 127)},
    };
    if (desconhecido) r["unknown"] = true;
    socket.send(zmq::buffer(r.dump()), zmq::send_flags::none);
}

void ServidorConsulta::handleMessage(cMessage *msg) {
    if (msg == fimMsg) {
        responder();
        servir();
        return;
    }
    if (msg == guardaMsg) {
        if (emVoo) {
            emVoo = false;
            perdido = true;
            atraso = (simTime() - inicio).dbl();
            responder();
            servir();
        }
        return;
    }
    delete msg;
}

void ServidorConsulta::finish() {
    cancelAndDelete(fimMsg);
    cancelAndDelete(guardaMsg);
    fimMsg = guardaMsg = nullptr;
    socket.close();
}
