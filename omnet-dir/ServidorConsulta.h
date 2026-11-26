/**
 * @file ServidorConsulta.h
 * @brief Modo de consulta por mensagem: a rede do TSCC como servidor de rotas.
 *
 * O MosaikBridge transporta as mensagens no passo do Mosaik. No mercado
 * transativo do OpenTES a negociação inteira acontece dentro de UM passo de
 * 15 min, com o relógio da co-simulação parado, então não há passo onde
 * encaixar as mensagens. Neste modo cada envio de um agente vira uma consulta
 * ZMQ {origem, destino, bytes}: o servidor injeta um AgentPacket no AgentNode de
 * origem, a simulação o leva pelos mesmos nós, filas e canais da topologia, e a
 * resposta traz o atraso, o descarte e os saltos daquela mensagem.
 *
 * O contrato é o do servidor de rotas do co-simulation-opentes
 * (`comm-opentes/Tisch.cc`): {"action": "route", "src", "dst", "bytes"} ->
 * {"status", "dropped", "delay", "hops", "frames"}, mais "info" e "stop".
 */
#ifndef SERVIDOR_CONSULTA_H
#define SERVIDOR_CONSULTA_H

#include <omnetpp.h>
#include <zmq.hpp>
#include <nlohmann/json.hpp>

#include <map>
#include <set>
#include <string>

// Tipo (kind) do AgentPacket que pertence a uma consulta. O AgentNode o usa para
// avisar o servidor da entrega ou do descarte, e para não acumular a mensagem
// nas saídas do Mosaik (val_out), que neste modo ninguém lê.
#define KIND_CONSULTA 77

class ServidorConsulta : public omnetpp::cSimpleModule {
  private:
    zmq::context_t contexto{1};
    zmq::socket_t socket{contexto, zmq::socket_type::rep};

    std::map<std::string, omnetpp::cModule*> nos;   // nome do módulo -> AgentNode
    std::set<std::string> desconhecidos;             // nomes sem nó, avisados uma vez

    bool emVoo = false;
    bool perdido = false;
    bool enviado = false;   // a consulta virou pacote na rede
    int saltos = 0;
    long bytes = 0;
    double atraso = 0.0;
    omnetpp::simtime_t inicio;
    omnetpp::cMessage *fimMsg = nullptr;     // responde no mesmo instante, fora da pilha do AgentNode
    omnetpp::cMessage *guardaMsg = nullptr;  // descarte que nenhum caminho do AgentNode avisou

    omnetpp::cModule *resolver(const std::string& nome);
    void servir();
    void iniciar(const nlohmann::json& pedido);
    void responder(bool desconhecido = false);
    nlohmann::json info();

  protected:
    virtual int numInitStages() const override { return 2; }
    virtual void initialize(int stage) override;
    virtual void handleMessage(omnetpp::cMessage *msg) override;
    virtual void finish() override;

  public:
    // Chamados pelo AgentNode, para o pacote da consulta em curso.
    void contarSalto();
    void concluir(bool foiPerdido);
};

#endif
