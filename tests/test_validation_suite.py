#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_validation_suite.py — Suíte de validação automatizada do tscc-com-opentes.

Testa:
  1. Compilação C++17 e física de rede em omnet-dir/AgentNode.cc:
     - Suporte a cDatarateChannel (getChannelDelay / setChannelDelay)
     - Atraso de propagação espacial (dist * 0.00005 s; meio guiado ~5 ns/m)
     - Descarte por PER nativo do canal (pkt->hasBitError())
     - Limite de fila por porta (buffer overflow >= 5 pacotes enfileirados)
     - Meio guiado (Fibra) sem atenuação espacial
     - Roteamento multi-salto (BFS) e encaminhamento (packets_forwarded)
     - Semente determinística (RANDOM_SEED)
  2. Sincronismo de passo (mosaik_step, time_resolution, packets_forwarded) em MosaikBridge.cc
  3. Consistência de contagem de agentes, DynamicNetwork.ned e links.json nas 5 topologias
  4. Co-simulação fim a fim (PADE + Mosaik + emulador OMNeT++ ZMQ + Collector + Plotters):
     - Estrela (N=20 periféricos -> 21 agentes, 20 enlaces)
     - Malha completa (N=5 -> 5 agentes, 10 enlaces)
     - Anel bidirecional (N=5 -> 5 agentes, 5 enlaces)
     - Árvore radial (fan-out 2,2,2 -> 15 nós, 14 enlaces, encaminhamento multi-salto)
     - Híbrida (3 subestações, 1 concentrador/sub, 3 medidores/concentrador -> 16 nós)
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import pandas as pd
import pytest

from cosim.catalogo import TOPOLOGIAS

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OMNET_DIR = os.path.join(ROOT_DIR, 'omnet-dir')
MOSAIK_DIR = os.path.join(ROOT_DIR, 'mosaik-dir')
PADE_AGENTS_DIR = os.path.join(ROOT_DIR, 'pade-dir', 'pade_agents')
EMULATOR_SCRIPT = os.path.join(ROOT_DIR, 'tests', 'omnet_zmq_emulator.py')


def _get_free_port(start_port=16000, span=20):
    """Encontra um bloco de portas TCP livres consecutivas (necessário para PADE)."""
    for base in range(start_port, 60000, span + 5):
        ok = True
        for p in range(base, base + span):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', p)) == 0:
                    ok = False
                    break
        if ok:
            return base
    raise RuntimeError("Não foi possível alocar bloco de portas livres.")


# ══════════════════════════════════════════════════════════════
# 1. TESTE DE COMPILAÇÃO E FÍSICA C++17 (AgentNode.cc & MosaikBridge.cc)
# ══════════════════════════════════════════════════════════════

MOCK_OMNETPP_H = r"""
#pragma once
#include <string>
#include <vector>
#include <deque>
#include <map>
#include <iostream>
#include <sstream>
#include <cmath>
#include <cstdint>

namespace omnetpp {

class SimTime {
    double t;
public:
    SimTime(double v = 0.0) : t(v) {}
    double dbl() const { return t; }
    SimTime operator-(const SimTime& o) const { return SimTime(t - o.t); }
    SimTime operator+(const SimTime& o) const { return SimTime(t + o.t); }
};

inline SimTime simTime() { return SimTime(1.0); }

class cPar {
    double dval = 0.0;
    std::string sval;
public:
    cPar() = default;
    cPar(double d) : dval(d) {}
    double doubleValue() const { return dval; }
    void setDoubleValue(double d) { dval = d; }
    cPar& operator=(double d) { dval = d; return *this; }
    std::string stdstringValue() const { return sval; }
    void setStringValue(const char* s) { sval = s ? s : ""; }
    void setStringValue(const std::string& s) { sval = s; }
};

class cObject {
public:
    virtual ~cObject() = default;
};

class cComponentType : public cObject {
    std::string typeName;
public:
    cComponentType(const std::string& n = "") : typeName(n) {}
    const char* getName() const { return typeName.c_str(); }
    void setName(const std::string& n) { typeName = n; }
};

class cChannel : public cObject {
protected:
    std::map<std::string, cPar> params;
    bool busyFlag = false;
    cComponentType componentType{"Link_5G"};   // canal não guiado por padrão
public:
    cChannel() { params["delay"] = cPar(0.001); }
    cComponentType* getComponentType() { return &componentType; }
    void setTypeName(const std::string& n) { componentType.setName(n); }
    bool hasPar(const char* name) const { return params.count(name) > 0; }
    cPar& par(const char* name) { return params[name]; }
    void setBusy(bool b) { busyFlag = b; }
    virtual bool isBusy() const { return busyFlag; }
    virtual SimTime getTransmissionFinishTime() const { return SimTime(1.01); }
};

class cDelayChannel : public cChannel {
public:
    SimTime getDelay() const {
        auto it = params.find("delay");
        return SimTime(it != params.end() ? it->second.doubleValue() : 0.0);
    }
    void setDelay(double d) { params["delay"].setDoubleValue(d); }
};

class cDatarateChannel : public cChannel {
public:
    SimTime getDelay() const {
        auto it = params.find("delay");
        return SimTime(it != params.end() ? it->second.doubleValue() : 0.0);
    }
    void setDelay(double d) { params["delay"].setDoubleValue(d); }
};

class cModule;

class cGate : public cObject {
    cChannel* ch = nullptr;
    cGate* pathEnd = nullptr;
    cModule* ownerMod = nullptr;
    int idx = 0;
public:
    cGate(cModule* owner = nullptr) : ownerMod(owner) {}
    int getIndex() const { return idx; }
    void setIndex(int i) { idx = i; }
    void setChannel(cChannel* c) { ch = c; }
    void setPathEndGate(cGate* g) { pathEnd = g; }
    cGate* getPathEndGate() const { return pathEnd; }
    cChannel* getTransmissionChannel() const { return ch; }
    cModule* getOwnerModule() const { return ownerMod; }
};

class cMessage : public cObject {
    std::string name;
    SimTime creationTime = SimTime(0.95);
    void* ctxPtr = nullptr;
    bool selfMsg = false;
    cGate* arrivalGate = nullptr;
public:
    cMessage(const char* n = "") : name(n ? n : "") {}
    virtual ~cMessage() = default;
    cGate* getArrivalGate() const { return arrivalGate; }
    void setArrivalGate(cGate* g) { arrivalGate = g; }
    SimTime getCreationTime() const { return creationTime; }
    void setCreationTime(SimTime t) { creationTime = t; }
    void setContextPointer(void* p) { ctxPtr = p; }
    void* getContextPointer() const { return ctxPtr; }
    void setSelfMessage(bool b) { selfMsg = b; }
    bool isSelfMessage() const { return selfMsg; }
    virtual bool isPacket() const { return false; }
};

class cPacket : public cMessage {
    int64_t byteLen = 0;
    bool bitErr = false;
public:
    cPacket(const char* n = "") : cMessage(n) {}
    bool isPacket() const override { return true; }
    void setByteLength(int64_t l) { byteLen = l; }
    int64_t getByteLength() const { return byteLen; }
    void setBitError(bool b) { bitErr = b; }
    bool hasBitError() const { return bitErr; }
};

class cPacketQueue : public cObject {
    std::deque<cPacket*> q;
public:
    cPacketQueue(const char* = "") {}
    ~cPacketQueue() override {
        for (auto* p : q) delete p;
    }
    bool isEmpty() const { return q.empty(); }
    int getLength() const { return static_cast<int>(q.size()); }
    void insert(cPacket* p) { q.push_back(p); }
    cPacket* pop() {
        cPacket* p = q.front();
        q.pop_front();
        return p;
    }
};

class cModule : public cObject {
protected:
    std::string modName;
    int modId = 1;
    std::map<std::string, cPar> params;
    std::vector<cGate*> outGates;
    std::vector<cGate*> inGates;
public:
    cModule(const std::string& n = "node") : modName(n) {
        params["xPos"] = cPar(500.0);
        params["yPos"] = cPar(500.0);
        params["val_in"] = cPar(0.0);
        params["val_out"] = cPar(0.0);
        params["packets_sent"] = cPar(0.0);
        params["packets_received"] = cPar(0.0);
        params["packets_dropped"] = cPar(0.0);
        params["packets_forwarded"] = cPar(0.0);
        params["packet_sizes_out"] = cPar(0.0);
        params["latencies_out"] = cPar(0.0);
        params["jitters_out"] = cPar(0.0);
    }
    virtual ~cModule() = default;
    const char* getName() const { return modName.c_str(); }
    void setName(const std::string& n) { modName = n; }
    int getId() const { return modId; }
    bool hasPar(const char* name) const { return params.count(name) > 0; }
    cPar& par(const char* name) { return params[name]; }
    int gateSize(const char*) const { return static_cast<int>(outGates.size()); }
    cGate* gate(const char* name, int idx) {
        if (std::string(name) == "port$o") return outGates.at(idx);
        return inGates.at(idx);
    }
    void addPortPair(cGate* outG, cGate* inG) {
        outG->setIndex(static_cast<int>(outGates.size()));
        inG->setIndex(static_cast<int>(inGates.size()));
        outGates.push_back(outG);
        inGates.push_back(inG);
    }
};

class cSimpleModule : public cModule {
public:
    std::vector<cMessage*> sentMessages;
    cSimpleModule() = default;
    virtual void initialize() {}
    virtual void handleMessage(cMessage*) {}
    virtual void handleParameterChange(const char*) {}
    void send(cMessage* msg, const char*, int) {
        sentMessages.push_back(msg);
    }
    void scheduleAt(SimTime, cMessage* msg) {
        msg->setSelfMessage(true);
    }
    void cancelAndDelete(cMessage* msg) {
        delete msg;
    }
};

template <typename T, typename U>
T check_and_cast(U* p) {
    return dynamic_cast<T>(p);
}

#define Define_Module(CLASSNAME)
#define Enter_Method(NAME)
#define EV std::cout

} // namespace omnetpp
"""

MOCK_NLOHMANN_JSON_H = r"""
#pragma once
#include <string>
#include <vector>

namespace nlohmann {

class json_item {
    std::string val;
public:
    json_item(const std::string& v = "") : val(v) {}
    template <typename T>
    T get() const { return val; }
};

class json {
    std::vector<json_item> receivers_list;
public:
    static json parse(const std::string& s) {
        json j;
        auto pos = s.find("\"receivers\"");
        if (pos != std::string::npos) {
            auto lb = s.find('[', pos);
            auto rb = s.find(']', lb);
            if (lb != std::string::npos && rb != std::string::npos) {
                std::string arr = s.substr(lb + 1, rb - lb - 1);
                size_t q1 = 0;
                while ((q1 = arr.find('"', q1)) != std::string::npos) {
                    size_t q2 = arr.find('"', q1 + 1);
                    if (q2 == std::string::npos) break;
                    j.receivers_list.emplace_back(arr.substr(q1 + 1, q2 - q1 - 1));
                    q1 = q2 + 1;
                }
            }
        }
        return j;
    }
    bool contains(const std::string& k) const {
        return k == "receivers" && !receivers_list.empty();
    }
    const std::vector<json_item>& operator[](const std::string&) const {
        return receivers_list;
    }
};

} // namespace nlohmann
"""

MOCK_AGENTPACKET_H = r"""
#pragma once
#include <omnetpp.h>
#include <string>

class AgentPacket : public omnetpp::cPacket {
    std::string srcId;
    std::string dstId;
    std::string payloadStr;
public:
    AgentPacket(const char* name = "") : omnetpp::cPacket(name) {}
    void setSrcAgent(const char* s) { srcId = s ? s : ""; }
    const char* getSrcAgent() const { return srcId.c_str(); }
    void setDestAgent(const char* d) { dstId = d ? d : ""; }
    const char* getDestAgent() const { return dstId.c_str(); }
    void setPayload(const char* p) { payloadStr = p ? p : ""; }
    const char* getPayload() const { return payloadStr.c_str(); }
};
"""

CPP_TEST_DRIVER = r"""
#include "AgentNode.cc"
#include <cassert>
#include <cmath>
#include <iostream>

class TestAgentNode : public AgentNode {
public:
    using AgentNode::initialize;
    using AgentNode::handleMessage;
    using AgentNode::handleParameterChange;
    virtual ~TestAgentNode() override = default;
};

int main() {
    // Configura dois nós conectados por um cDatarateChannel (como em Profiles.ned)
    TestAgentNode central;
    central.setName("agent_central");
    central.par("xPos").setDoubleValue(500.0);
    central.par("yPos").setDoubleValue(500.0);

    TestAgentNode periferico;
    periferico.setName("agent_p_1");
    periferico.par("xPos").setDoubleValue(600.0); // dist = 100m -> propDelay = 0.005s
    periferico.par("yPos").setDoubleValue(500.0);

    cDatarateChannel chanOut, chanIn;    // tipo padrão do mock: Link_5G (meio não guiado)
    chanOut.setDelay(0.001); // 1ms base delay
    chanIn.setDelay(0.001);

    cGate outG(&central), inG(&central);
    cGate peerOut(&periferico), peerIn(&periferico);
    outG.setChannel(&chanOut);
    outG.setPathEndGate(&peerIn);
    peerOut.setChannel(&chanIn);
    peerOut.setPathEndGate(&inG);
    central.addPortPair(&outG, &inG);
    periferico.addPortPair(&peerOut, &peerIn);

    central.initialize();
    periferico.initialize();

    // Teste 1: Atraso de propagação espacial aplicado sobre cDatarateChannel (0.001 + 100*0.00005 = 0.006s)
    assert(std::abs(chanOut.getDelay().dbl() - 0.006) < 1e-6);
    assert(std::abs(chanIn.getDelay().dbl() - 0.006) < 1e-6);

    // Teste 2: Envio em rajada quando canal está ocupado -> fila limita a 5 pacotes e descarta o excedente
    chanOut.setBusy(true);
    std::string m = "{\"sender\":\"AgenteCentral\",\"receivers\":[\"AgenteP_1@0.0.0.0:5679\"]}";
    std::string burst = m + "|||" + m + "|||" + m + "|||" + m + "|||" + m + "|||" + m + "|||" + m + "|||" + m;
    central.par("val_in").setStringValue(burst);
    central.handleParameterChange("val_in");

    assert(central.par("packets_sent").doubleValue() == 8.0);
    assert(central.par("packets_dropped").doubleValue() == 3.0);

    // Teste 3: Descarte por PER nativo do canal (pkt->hasBitError() == true)
    AgentPacket* errPkt = new AgentPacket("corrupted");
    errPkt->setSrcAgent("agent_central");
    errPkt->setDestAgent("agent_p_1");
    errPkt->setPayload("{\"sender\":\"AgenteCentral\"}");
    errPkt->setByteLength(120);
    errPkt->setBitError(true);
    periferico.handleMessage(errPkt);

    assert(periferico.par("packets_dropped").doubleValue() == 1.0);
    assert(periferico.par("packets_received").doubleValue() == 0.0);

    // Teste 4: Recepção válida sem erro de bit
    // Posiciona vizinho próximo (dist = 0 -> inDropChances = 0) para recepção determinística
    AgentPacket* okPkt = new AgentPacket("valid");
    okPkt->setSrcAgent("local_peer");
    okPkt->setDestAgent("agent_p_1");
    okPkt->setPayload("{\"sender\":\"AgenteCentral\"}");
    okPkt->setByteLength(200);
    okPkt->setBitError(false);
    okPkt->setCreationTime(SimTime(0.974));
    periferico.handleMessage(okPkt);

    assert(periferico.par("packets_received").doubleValue() == 1.0);
    assert(periferico.par("val_out").stdstringValue() == "{\"sender\":\"AgenteCentral\"}");
    assert(!periferico.par("latencies_out").stdstringValue().empty());

    // Teste 5: Meio guiado (Fibra) — propagação de ~5 ns/m e sem atenuação espacial
    TestAgentNode fa, fb;
    fa.setName("fibra_a");
    fb.setName("fibra_b");
    fa.par("xPos").setDoubleValue(0.0);
    fa.par("yPos").setDoubleValue(0.0);
    fb.par("xPos").setDoubleValue(10000.0);   // 10 km
    fb.par("yPos").setDoubleValue(0.0);
    cDatarateChannel fibAB, fibBA;
    fibAB.setTypeName("Fibra");
    fibBA.setTypeName("Fibra");
    fibAB.setDelay(0.00005);
    fibBA.setDelay(0.00005);
    cGate faOut(&fa), faIn(&fa), fbOut(&fb), fbIn(&fb);
    faOut.setChannel(&fibAB);
    faOut.setPathEndGate(&fbIn);
    fbOut.setChannel(&fibBA);
    fbOut.setPathEndGate(&faIn);
    fa.addPortPair(&faOut, &faIn);
    fb.addPortPair(&fbOut, &fbIn);
    fa.initialize();
    fb.initialize();
    assert(std::abs(fibAB.getDelay().dbl() - (0.00005 + 10000.0 * 5e-9)) < 1e-12);

    // A 10 km, um meio não guiado teria 99% de perda espacial; na fibra só vale o PER.
    AgentPacket* fibPkt = new AgentPacket("fibra");
    fibPkt->setSrcAgent("fibra_a");
    fibPkt->setDestAgent("fibra_b");
    fibPkt->setPayload("{\"sender\":\"fibra_a\"}");
    fibPkt->setByteLength(100);
    fibPkt->setArrivalGate(&fbIn);
    fb.handleMessage(fibPkt);
    assert(fb.par("packets_received").doubleValue() == 1.0);
    assert(fb.par("packets_dropped").doubleValue() == 0.0);

    // Teste 6: Roteamento multi-salto (BFS) e encaminhamento no nó intermediário
    //   ra <--> rb <--> rc   (posições coincidentes: sem perda espacial)
    TestAgentNode ra, rb, rc;
    ra.setName("ra");
    rb.setName("rb");
    rc.setName("rc");
    cDatarateChannel chAB, chBA, chBC, chCB;
    cGate aOut(&ra), aIn(&ra), bOut0(&rb), bIn0(&rb), bOut1(&rb), bIn1(&rb), cOut(&rc), cIn(&rc);
    aOut.setChannel(&chAB);
    aOut.setPathEndGate(&bIn0);
    bOut0.setChannel(&chBA);
    bOut0.setPathEndGate(&aIn);
    bOut1.setChannel(&chBC);
    bOut1.setPathEndGate(&cIn);
    cOut.setChannel(&chCB);
    cOut.setPathEndGate(&bIn1);
    ra.addPortPair(&aOut, &aIn);
    rb.addPortPair(&bOut0, &bIn0);
    rb.addPortPair(&bOut1, &bIn1);
    rc.addPortPair(&cOut, &cIn);
    ra.initialize();
    rb.initialize();
    rc.initialize();

    // rc não é vizinho de ra, mas a tabela de rotas encontra o caminho via rb
    ra.par("val_in").setStringValue("{\"sender\":\"ra\",\"receivers\":[\"rc@0.0.0.0:1\"]}");
    ra.handleParameterChange("val_in");
    assert(ra.par("packets_sent").doubleValue() == 1.0);
    assert(ra.sentMessages.size() == 1);

    // rb recebe um pacote destinado a rc: encaminha em vez de entregar
    AgentPacket* fwdPkt = new AgentPacket("transito");
    fwdPkt->setSrcAgent("ra");
    fwdPkt->setDestAgent("rc");
    fwdPkt->setPayload("{\"sender\":\"ra\"}");
    fwdPkt->setByteLength(100);
    fwdPkt->setArrivalGate(&bIn0);
    rb.handleMessage(fwdPkt);
    assert(rb.par("packets_forwarded").doubleValue() == 1.0);
    assert(rb.par("packets_received").doubleValue() == 0.0);
    assert(rb.sentMessages.size() == 1);

    // rc é o destino final: entrega ao agente
    AgentPacket* finalPkt = new AgentPacket("final");
    finalPkt->setSrcAgent("ra");
    finalPkt->setDestAgent("rc");
    finalPkt->setPayload("{\"sender\":\"ra\"}");
    finalPkt->setByteLength(100);
    finalPkt->setArrivalGate(&cIn);
    rc.handleMessage(finalPkt);
    assert(rc.par("packets_received").doubleValue() == 1.0);
    assert(rc.par("val_out").stdstringValue() == "{\"sender\":\"ra\"}");

    std::cout << "ALL_CPP_TESTS_PASSED" << std::endl;
    return 0;
}
"""


def test_cpp_agentnode_and_mosaikbridge_physics():
    """Compila AgentNode.cc com C++17 (ziglang c++) e valida física de canal, PER e overflow."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        os.makedirs(os.path.join(tmpdir, 'nlohmann'), exist_ok=True)
        with open(os.path.join(tmpdir, 'omnetpp.h'), 'w', encoding='utf-8') as f:
            f.write(MOCK_OMNETPP_H)
        with open(os.path.join(tmpdir, 'nlohmann', 'json.hpp'), 'w', encoding='utf-8') as f:
            f.write(MOCK_NLOHMANN_JSON_H)
        with open(os.path.join(tmpdir, 'AgentPacket_m.h'), 'w', encoding='utf-8') as f:
            f.write(MOCK_AGENTPACKET_H)
        shutil.copy(os.path.join(OMNET_DIR, 'AgentNode.cc'), os.path.join(tmpdir, 'AgentNode.cc'))
        test_cpp_path = os.path.join(tmpdir, 'test_driver.cc')
        with open(test_cpp_path, 'w', encoding='utf-8') as f:
            f.write(CPP_TEST_DRIVER)

        exe_path = os.path.join(tmpdir, 'test_driver.exe')
        compile_cmd = [
            sys.executable, '-m', 'ziglang', 'c++',
            '-std=c++17', '-Wno-nullability-completeness', '-I', tmpdir,
            test_cpp_path, '-o', exe_path
        ]
        res_compile = subprocess.run(compile_cmd, capture_output=True, text=True)
        assert res_compile.returncode == 0, f"Falha na compilação C++17:\n{res_compile.stderr}"

        env = os.environ.copy()
        env['RANDOM_SEED'] = '42'
        res_run = subprocess.run([exe_path], capture_output=True, text=True, env=env)
        assert res_run.returncode == 0, f"Falha na execução do binário C++:\n{res_run.stderr}"
        assert "ALL_CPP_TESTS_PASSED" in res_run.stdout

    # Valida também que MosaikBridge.cc contém o rastreamento de currentMosaikStep e time_resolution
    with open(os.path.join(OMNET_DIR, 'MosaikBridge.cc'), 'r', encoding='utf-8') as f:
        bridge_src = f.read()
    assert '{"mosaik_step", currentMosaikStep}' in bridge_src
    assert 'time_resolution' in bridge_src
    assert 'packets_forwarded' in bridge_src


# ══════════════════════════════════════════════════════════════
# 2. TESTE DE CO-SIMULAÇÃO INTEGRADA E2E NAS 5 TOPOLOGIAS
# ══════════════════════════════════════════════════════════════

# Script PADE de cada topologia (mesmo despacho do docker-compose.yml). O
# scenario.py chama o script de plotagem ao final, como no container mosaik_master.
PADE_SCRIPTS = {t.id: t.script_pade for t in TOPOLOGIAS.values()}
_EXTENSOES_GRAFICOS = ('.png', '.svg')


def _listar_graficos():
    return sorted(f for f in os.listdir(MOSAIK_DIR)
                  if f.startswith('grafico_') and f.endswith(_EXTENSOES_GRAFICOS))


def _contar_conexoes_ned():
    with open(os.path.join(OMNET_DIR, 'DynamicNetwork.ned'), encoding='utf-8') as f:
        return sum(1 for linha in f if '.port++ <-->' in linha)


def _truncar_logs_pade():
    """O data_logger do PADE acumula CSVs em pade_agents/logs/; mantém só o cabeçalho."""
    logs_dir = os.path.join(PADE_AGENTS_DIR, 'logs')
    if not os.path.isdir(logs_dir):
        return
    for fn in os.listdir(logs_dir):
        if fn.endswith('.csv'):
            p = os.path.join(logs_dir, fn)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    header = f.readline()
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(header)
            except OSError:
                pass


def _ultimo_valor(df, atributo):
    """Soma, entre todos os nós, o último valor registrado de um contador."""
    linhas = df[df['Atributo'] == atributo]
    if linhas.empty:
        return 0.0
    ultimos = linhas.sort_values('Tempo').groupby('Origem')['Valor'].last()
    return pd.to_numeric(ultimos, errors='coerce').fillna(0).sum()


def _run_e2e_cosimulation(topology, total_agentes, num_perifericos=3,
                          extra_env=None, sim_steps=20, seed=42):
    """
    Executa uma co-simulação completa (PADE + Mosaik + emulador OMNeT++ via ZMQ
    + Collector + plotagem) e retorna os artefatos gerados para inspeção.
    """
    offset = {'anel': 0, 'malha': 200, 'estrela': 400, 'arvore': 600, 'hibrida': 800}[topology]
    pade_port = _get_free_port(18000 + offset, span=total_agentes + 5)
    ams_port = _get_free_port(25000 + offset, span=2)
    omnet_port = _get_free_port(28000 + offset, span=2)

    env = os.environ.copy()
    env.update({
        'TOPOLOGY': topology,
        'NUM_PERIFERICOS': str(num_perifericos),
        'TIPOS_REDE': 'Link_Wired,Link_5G,Link_4G,Link_2G,Link_Wireless',
        'RANDOM_SEED': str(seed),
        'SIM_STEPS': str(sim_steps),
        'PADE_HOST': '127.0.0.1',
        'PADE_PORT': str(pade_port),
        'AMS_PORT': str(ams_port),
        'OMNET_HOST': '127.0.0.1',
        'OMNET_PORT': str(omnet_port),
        'OMNET_DIR': OMNET_DIR,
        'PYTHONIOENCODING': 'utf-8',
        'MPLBACKEND': 'Agg',
    })
    env.update(extra_env or {})

    # Remove gráficos de rodadas anteriores para confirmar que o plotter os recriou
    for fname in _listar_graficos():
        os.remove(os.path.join(MOSAIK_DIR, fname))

    with tempfile.TemporaryFile(mode='w+', encoding='utf-8', errors='replace') as pade_log, \
         tempfile.TemporaryFile(mode='w+', encoding='utf-8', errors='replace') as omnet_log:
        pade_proc = subprocess.Popen(
            [sys.executable, PADE_SCRIPTS[topology]],
            cwd=PADE_AGENTS_DIR, env=env, stdout=pade_log, stderr=subprocess.STDOUT,
        )
        omnet_proc = subprocess.Popen(
            [sys.executable, EMULATOR_SCRIPT],
            cwd=ROOT_DIR, env=env, stdout=omnet_log, stderr=subprocess.STDOUT,
        )
        try:
            mosaik_res = subprocess.run(
                [sys.executable, 'scenario.py'],
                cwd=MOSAIK_DIR, env=env, capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=240,
            )
            if mosaik_res.returncode != 0:
                pade_log.seek(0)
                omnet_log.seek(0)
                raise AssertionError(
                    f"scenario.py falhou para {topology}:\n"
                    f"STDOUT:\n{mosaik_res.stdout[-6000:]}\nSTDERR:\n{mosaik_res.stderr[-6000:]}\n"
                    f"PADE LOG:\n{pade_log.read()[-4000:]}\nOMNET LOG:\n{omnet_log.read()[-4000:]}"
                )
        finally:
            for proc in (pade_proc, omnet_proc):
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            _truncar_logs_pade()

    with open(os.path.join(OMNET_DIR, 'posicoes.json'), encoding='utf-8') as f:
        posicoes = json.load(f)
    with open(os.path.join(OMNET_DIR, 'links.json'), encoding='utf-8') as f:
        links = json.load(f)
    with open(os.path.join(OMNET_DIR, 'config.json'), encoding='utf-8') as f:
        config = json.load(f)
    df = pd.read_csv(os.path.join(MOSAIK_DIR, 'results.csv'))

    assert len(posicoes) == total_agentes, (
        f"{topology}: esperado {total_agentes} agentes, posicoes.json tem {len(posicoes)}")
    assert _contar_conexoes_ned() == len(links), "DynamicNetwork.ned e links.json divergem"
    assert config['topologia'] == topology
    return posicoes, links, config, df, _listar_graficos()


def _mensagens_entregues(df):
    return df[(df['Atributo'] == 'val_out') & (df['Valor'].notna()) & (df['Valor'] != '')]


def test_e2e_anel_topology():
    """Anel: N=5 agentes peers, 5 enlaces fechando o ciclo."""
    posicoes, links, _, df, graficos = _run_e2e_cosimulation('anel', total_agentes=5, num_perifericos=5)

    assert [ag['id'] for ag in posicoes] == ['agente_1', 'agente_2', 'agente_3', 'agente_4', 'agente_5']
    assert len(links) == 5, "Anel de 5 agentes deve possuir 5 enlaces fechando o ciclo."
    assert not _mensagens_entregues(df).empty, "O CSV deve registrar mensagens entregues no anel."
    assert 'grafico_trafego_Anel.svg' in graficos
    assert 'grafico_trafego_Geral.svg' in graficos


def test_e2e_malha_topology():
    """Malha completa: N=5 agentes no total (semântica de menu.py), 10 enlaces."""
    _, links, _, df, graficos = _run_e2e_cosimulation('malha', total_agentes=5, num_perifericos=5)

    assert len(links) == 10, "Malha de 5 agentes deve possuir 5*4/2 = 10 enlaces bidirecionais."
    assert len(_mensagens_entregues(df)) >= 50, \
        "Todos os 5 agentes da malha devem trocar mensagens em todos os passos."
    assert 'grafico_trafego_Geral.png' in graficos
    for tech in ('Cabeada', '5G', '4G', '2G', 'Wireless'):
        assert f'grafico_trafego_{tech}.png' in graficos


def test_e2e_estrela_topology():
    """Estrela: N=20 periféricos -> 21 agentes, 20 enlaces."""
    _, links, _, df, graficos = _run_e2e_cosimulation('estrela', total_agentes=21, num_perifericos=20)

    assert len(links) == 20, "Estrela de 20 periféricos deve possuir 20 enlaces."
    # O central faz poll em todos os periféricos a cada passo e recebe as respostas no
    # passo seguinte (time_shifted): no máximo 20 * 19 = 380 respostas em 20 passos.
    central_rx = df[
        (df['Origem'] == 'OmnetSim-0.agent_central')
        & (df['Atributo'] == 'packets_received')
        & (df['Tempo'] == 19)
    ]['Valor'].astype(float).iloc[0]
    assert central_rx > 200, f"Central deve receber >200 das 380 respostas possíveis (recebeu {central_rx})."
    for tech in ('Geral', 'Cabeada', '5G', '4G', '2G', 'Wireless'):
        assert f'grafico_trafego_{tech}.svg' in graficos


def test_e2e_arvore_topology():
    """Árvore radial IEC 61850 com fan-out 2,2,2: 1 + 2 + 4 + 8 = 15 nós e 14 enlaces."""
    posicoes, links, config, df, graficos = _run_e2e_cosimulation(
        'arvore', total_agentes=15, extra_env={'ARVORE_FANOUT': '2,2,2', 'CELULAR_ARVORE': '4g'})

    assert len(links) == 14, "Uma árvore com 15 nós deve ter 14 enlaces."
    assert config['arvore_fanout'] == '2,2,2'
    assert {ag['camada'] for ag in posicoes} == {'controle', 'subestacao', 'concentrador', 'medidor'}
    assert {lk['tipo'] for lk in links} == {'Fibra', 'Celular4G', 'PLC'}
    assert not _mensagens_entregues(df).empty
    assert _ultimo_valor(df, 'packets_forwarded') > 0, \
        "Mensagens entre raiz e medidores atravessam vários saltos e precisam ser encaminhadas."
    assert 'grafico_trafego_Arvore.svg' in graficos
    assert 'grafico_trafego_Geral.svg' in graficos


def test_e2e_hibrida_topology():
    """Híbrida: CCO + 3 subestações (anel de fibra) + 1 concentrador/sub + 3 medidores/concentrador."""
    _, links, config, df, graficos = _run_e2e_cosimulation(
        'hibrida', total_agentes=1 + 3 + 3 + 9,
        extra_env={'SUBESTACOES': '3', 'CONCENTRADORES': '1', 'MEDIDORES_CLUSTER': '3',
                   'CELULAR_HIBRIDA': '4g', 'SEMENTE_HIBRIDA': '42'})

    tipos = {lk['tipo'] for lk in links}
    assert {'Fibra', 'Celular4G', 'RFMesh'} <= tipos
    assert sum(1 for lk in links if lk['tipo'] == 'Fibra') == 3 + 2, \
        "Anel de 3 subestações (3 enlaces) + CCO ligado a 2 subestações."
    assert config['subestacoes'] == 3
    assert not _mensagens_entregues(df).empty
    assert _ultimo_valor(df, 'packets_forwarded') > 0, \
        "Mensagens entre CCO e medidores atravessam vários saltos e precisam ser encaminhadas."
    assert 'grafico_trafego_Hibrida.svg' in graficos
    assert 'grafico_trafego_Geral.svg' in graficos
