/**
 * @file ExtensaoOpenTES.h
 * @brief Extensões do AgentNode para o mercado transativo do OpenTES (IEEE 13 barras).
 *
 * Tudo aqui é opcional e não altera o comportamento original do AgentNode:
 *
 *  - Canais do modelo da tese (Melo, 2022, seção 6.1.5), `Link_6TiSCH_TSCH` e
 *    `Link_WiSUN_FAN` em Profiles.ned. Neles o atraso e a perda de cada salto
 *    seguem o MAC do rádio: TSCH (slotframe, cells, quadro de 127 B,
 *    fragmentação, retentativas) ou CSMA/CA do Wi-SUN FAN, com o PER do enlace
 *    calculado na montagem da topologia (Friis, Pister-Hack e tabela de PER, em
 *    cosim/radio.py). Os demais canais seguem o modelo do repositório.
 *  - Roteamento por ETX da mensagem (`roteamento = "etx"`), além do BFS em
 *    número de saltos.
 *  - Modo de consulta por mensagem (ServidorConsulta).
 *  - Nomes dos agentes PADE lidos de arquivo (`arquivo_nomes`) e a regra
 *    "nome -> agent_<nome em minúsculas>".
 *
 * O AgentNode.cc só inclui este arquivo quando ele existe (`__has_include`), o
 * que mantém o teste de física C++ do repositório compilando o modelo original.
 */
#ifndef EXTENSAO_OPENTES_H
#define EXTENSAO_OPENTES_H

#include <omnetpp.h>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <limits>
#include <map>
#include <queue>
#include <sstream>
#include <string>
#include <vector>

#include "ServidorConsulta.h"

#define KIND_PERDA_TESE 78

namespace opentes {

using namespace omnetpp;

inline std::string minusculas(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return std::tolower(c); });
    return s;
}

// Parâmetros de um enlace dos canais da tese, lidos do canal na inicialização.
struct EnlaceTese {
    bool wisun = false;
    double per = 0.0;         // PER de um quadro de 127 B neste enlace
    double slotframe = 4.04;  // TSCH
    int cells = 2;
    int quadro = 127;         // bytes por quadro: 127 no TSCH, 1280 no Wi-SUN
    int retries = 3;          // macMaxFrameRetries
    double taxa = 50000.0;    // Wi-SUN: taxa da camada física
    int minBE = 3, maxBE = 5, shrPhr = 12, ack = 30;
    double unitBackoff = 0.00116, turnaround = 0.001;
};

// Lê o enlace se o canal for um dos da tese (tem o parâmetro `mac`). O tempo do
// salto vem do MAC: o AgentNode envia com duração zero e atraso do próprio salto.
inline bool lerEnlaceTese(cChannel *c, EnlaceTese& e) {
    if (!c || !c->hasPar("mac")) return false;
    e.wisun = c->par("mac").stdstringValue() == "wisun";
    e.per = c->par("per_enlace").doubleValue();
    e.quadro = c->par("quadro_bytes").intValue();
    e.retries = c->par("max_retries").intValue();
    if (auto *dr = dynamic_cast<cDatarateChannel*>(c)) {
        e.taxa = dr->getDatarate();
        dr->setDelay(0);
    }
    if (e.wisun) {
        if (c->par("taxa_bps").doubleValue() > 0) e.taxa = c->par("taxa_bps").doubleValue();
        e.minBE = c->par("min_be").intValue();
        e.maxBE = c->par("max_be").intValue();
        e.unitBackoff = c->par("unit_backoff").doubleValue();
        e.turnaround = c->par("turnaround").doubleValue();
        e.shrPhr = c->par("shr_phr_bytes").intValue();
        e.ack = c->par("ack_bytes").intValue();
    } else {
        e.slotframe = c->par("slotframe").doubleValue();
        e.cells = c->par("cells").intValue();
    }
    return true;
}

// PER do quadro do MAC: a tabela é de um quadro de 127 B; um quadro maior tem
// mais bits para errar, PER(L) = 1 - (1 - PER(127))^(L/127).
inline double perQuadro(const EnlaceTese& e) {
    if (e.quadro <= 127) return e.per;
    return 1.0 - std::pow(1.0 - e.per, e.quadro / 127.0);
}

inline int quadros(const EnlaceTese& e, long bytes) {
    return (int)std::max(1L, (bytes + e.quadro - 1) / e.quadro);
}

// Atraso de um salto e se a mensagem se perdeu nele, como no servidor 6TiSCH do
// co-simulation-opentes. Perder um fragmento perde o datagrama inteiro.
inline double atrasoTese(cComponent *m, const EnlaceTese& e, long bytes, bool& perdido) {
    perdido = false;
    int n = quadros(e, bytes);
    if (e.wisun) {
        // CSMA/CA não sincronizado: recuo + tempo no ar + reversão + ACK + LIFS.
        double ar = (e.quadro + e.shrPhr) * 8.0 / e.taxa;
        double tAck = e.turnaround + (e.ack + e.shrPhr) * 8.0 / e.taxa;
        double lifs = 40.0 / e.taxa;
        double p = perQuadro(e);
        double atraso = 0.0;
        for (int f = 0; f < n; ++f) {
            int be = e.minBE;
            for (int tentativa = 0;; ++tentativa) {
                atraso += m->intuniform(0, (1 << be) - 1) * e.unitBackoff + ar;
                if (m->uniform(0.0, 1.0) >= p) { atraso += tAck + lifs; break; }
                atraso += tAck;
                if (tentativa >= e.retries) { perdido = true; return atraso; }
                be = std::min(be + 1, e.maxBE);
            }
        }
        return atraso;
    }
    // TSCH: o quadro só sai no cell do enlace. O primeiro espera uma fração do
    // slotframe; os seguintes, um espaçamento entre cells; cada retentativa gasta
    // mais um cell.
    double espaco = e.slotframe / std::max(1, e.cells);
    double atraso = m->uniform(0.0, e.slotframe);
    for (int f = 0; f < n; ++f) {
        if (f > 0) atraso += espaco;
        int tentativa = 0;
        while (m->uniform(0.0, 1.0) < e.per) {
            atraso += espaco;
            if (++tentativa > e.retries) { perdido = true; return atraso; }
        }
    }
    return atraso;
}

// Custo de um enlace em número esperado de transmissões para entregar a
// mensagem inteira (ETX do datagrama). Depende do tamanho: um enlace razoável
// para um quadro pode ser inútil para uma mensagem de 281 quadros.
inline double custoEtx(cChannel *c, long bytes) {
    EnlaceTese e;
    if (c && c->hasPar("mac")) {
        e.per = c->par("per_enlace").doubleValue();
        e.quadro = c->par("quadro_bytes").intValue();
        e.retries = c->par("max_retries").intValue();
        double pQ = std::pow(perQuadro(e), e.retries + 1);
        int n = quadros(e, bytes);
        double pD = 1.0 - std::pow(1.0 - pQ, n);
        return n / std::max(1e-9, 1.0 - pD);
    }
    double per = (c && c->hasPar("per")) ? c->par("per").doubleValue() : 0.0;
    return 1.0 / std::max(1e-9, 1.0 - per);
}

// Porta deste nó que inicia o caminho de menor ETX até `destino` (Dijkstra sobre
// o grafo de portas dos AgentNodes), ou -1 se não houver caminho.
inline int primeiraPortaEtx(cModule *origem, const std::string& destino, long bytes) {
    std::map<cModule*, double> dist;
    std::map<cModule*, int> primeira;
    using Item = std::pair<double, cModule*>;
    std::priority_queue<Item, std::vector<Item>, std::greater<Item>> fila;
    dist[origem] = 0.0;
    primeira[origem] = -1;
    fila.push({0.0, origem});
    while (!fila.empty()) {
        auto [d, u] = fila.top();
        fila.pop();
        if (d > dist[u] + 1e-12) continue;
        if (destino == u->getName()) return primeira[u];
        for (int p = 0; p < u->gateSize("port"); ++p) {
            cGate *og = u->gate("port$o", p);
            if (!og || !og->getPathEndGate()) continue;
            cModule *v = og->getPathEndGate()->getOwnerModule();
            double nd = d + custoEtx(og->getTransmissionChannel(), bytes);
            auto it = dist.find(v);
            if (it == dist.end() || nd < it->second - 1e-12) {
                dist[v] = nd;
                primeira[v] = (u == origem) ? p : primeira[u];
                fila.push({nd, v});
            }
        }
    }
    return -1;
}

// Tabela "nome do agente PADE,nó OMNeT++" (uma linha por agente, # comenta).
inline std::map<std::string, std::string> lerNomes(const std::string& caminho) {
    std::map<std::string, std::string> m;
    if (caminho.empty()) return m;
    std::ifstream f(caminho);
    if (!f) throw cRuntimeError("arquivo_nomes '%s' nao encontrado", caminho.c_str());
    std::string linha;
    while (std::getline(f, linha)) {
        if (linha.empty() || linha[0] == '#') continue;
        auto v = linha.find(',');
        if (v == std::string::npos) continue;
        m[linha.substr(0, v)] = linha.substr(v + 1);
    }
    return m;
}

}  // namespace opentes

#endif
