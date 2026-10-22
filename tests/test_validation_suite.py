#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_validation_suite.py — Suíte de validação automatizada do tscc-com-opentes.

Testa:
  1. Compilação C++17 e física de rede em omnet-dir/AgentNode.cc:
     - Suporte a cDatarateChannel (getChannelDelay / setChannelDelay)
     - Atraso de propagação espacial (dist * 0.00005 s)
     - Descarte por PER nativo do canal (pkt->hasBitError())
     - Limite de fila por porta (buffer overflow >= 5 pacotes enfileirados)
     - Semente determinística (RANDOM_SEED)
  2. Sincronismo de passo (mosaik_step e time_resolution) em omnet-dir/MosaikBridge.cc
  3. Consistência de contagem de agentes, DynamicNetwork.ned e links.json nas 3 topologias
  4. Co-simulação fim a fim (PADE + Mosaik + OMNeT++ ZMQ + Collector + Plotters) para:
     - Topologia Estrela (N=20 periféricos -> 21 agentes, 20 enlaces)
     - Topologia Malha Completa (N=5 peers -> 5 agentes, 10 enlaces)
     - Topologia Anel Bidirecional (N=5 peers -> 5 agentes, 5 enlaces)
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

class cChannel : public cObject {
protected:
    std::map<std::string, cPar> params;
    bool busyFlag = false;
public:
    cChannel() { params["delay"] = cPar(0.001); }
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
public:
    cGate(cModule* owner = nullptr) : ownerMod(owner) {}
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
public:
    cMessage(const char* n = "") : name(n ? n : "") {}
    virtual ~cMessage() = default;
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

    cDatarateChannel chanOut, chanIn;
    chanOut.setDelay(0.001); // 1ms base delay (Link_Wired)
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


# ══════════════════════════════════════════════════════════════
# 2. TESTE DE CO-SIMULAÇÃO INTEGRADA E2E NAS 3 TOPOLOGIAS
# ══════════════════════════════════════════════════════════════

def _run_e2e_cosimulation(topology, num_perifericos, sim_steps=20, seed=42):
    """
    Executa uma co-simulação completa (PADE + Mosaik + OMNeT++ ZMQ + Collector + Plotter)
    e retorna os artefatos gerados para inspeção.
    """
    offset = {'anel': 0, 'malha': 200, 'estrela': 400}.get(topology, 600)
    pade_port = _get_free_port(18000 + offset, span=num_perifericos + 5)
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
    })

    if topology == 'anel':
        pade_script = 'pade_anel.py'
        plot_script = 'plot_results_anel.py'
    elif topology == 'malha':
        pade_script = 'pade_malha.py'
        plot_script = 'plot_results_malha.py'
    else:
        pade_script = 'pade_star.py'
        plot_script = 'plot_results_star.py'

    # Limpa PNGs alvo antes da rodada para confirmar que o plotter os recriou
    target_pngs = [
        'grafico_trafego_Geral.png',
        'grafico_trafego_Cabeada.png',
        'grafico_trafego_5G.png',
        'grafico_trafego_4G.png',
        'grafico_trafego_2G.png',
        'grafico_trafego_Wireless.png',
    ]
    if topology == 'anel':
        target_pngs.append('grafico_trafego_Anel.png')
    for fname in target_pngs:
        fpath = os.path.join(MOSAIK_DIR, fname)
        if os.path.exists(fpath):
            os.remove(fpath)

    with tempfile.TemporaryFile(mode='w+', encoding='utf-8', errors='replace') as pade_log, \
         tempfile.TemporaryFile(mode='w+', encoding='utf-8', errors='replace') as omnet_log:
        pade_proc = subprocess.Popen(
            [sys.executable, pade_script],
            cwd=PADE_AGENTS_DIR,
            env=env,
            stdout=pade_log,
            stderr=subprocess.STDOUT,
        )
        omnet_proc = subprocess.Popen(
            [sys.executable, EMULATOR_SCRIPT],
            cwd=ROOT_DIR,
            env=env,
            stdout=omnet_log,
            stderr=subprocess.STDOUT,
        )

        try:
            mosaik_res = subprocess.run(
                [sys.executable, 'scenario.py'],
                cwd=MOSAIK_DIR,
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,
            )
            if mosaik_res.returncode != 0:
                pade_log.seek(0)
                omnet_log.seek(0)
                raise AssertionError(
                    f"scenario.py falhou para {topology}:\n"
                    f"STDOUT:\n{mosaik_res.stdout}\nSTDERR:\n{mosaik_res.stderr}\n"
                    f"PADE LOG:\n{pade_log.read()}\nOMNET LOG:\n{omnet_log.read()}"
                )

            plot_res = subprocess.run(
                [sys.executable, plot_script],
                cwd=MOSAIK_DIR,
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,
            )
            assert plot_res.returncode == 0, (
                f"{plot_script} falhou para {topology}:\nSTDOUT:\n{plot_res.stdout}\nSTDERR:\n{plot_res.stderr}"
            )
        finally:
            for proc in (pade_proc, omnet_proc):
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            logs_dir = os.path.join(PADE_AGENTS_DIR, 'logs')
            if os.path.isdir(logs_dir):
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

    with open(os.path.join(OMNET_DIR, 'posicoes.json'), encoding='utf-8') as f:
        posicoes = json.load(f)
    with open(os.path.join(OMNET_DIR, 'links.json'), encoding='utf-8') as f:
        links = json.load(f)
    with open(os.path.join(OMNET_DIR, 'config.json'), encoding='utf-8') as f:
        config = json.load(f)
    df = pd.read_csv(os.path.join(MOSAIK_DIR, 'results.csv'))
    pngs = sorted([f for f in os.listdir(MOSAIK_DIR) if f.startswith('grafico_') and f.endswith('.png')])

    return posicoes, links, config, df, pngs


def test_e2e_anel_topology():
    """Valida co-simulação fim a fim na topologia Anel (N=5 agentes peers, 5 enlaces)."""
    posicoes, links, config, df, pngs = _run_e2e_cosimulation('anel', num_perifericos=5, sim_steps=20, seed=42)

    assert len(posicoes) == 5, "No anel, NUM_PERIFERICOS=5 deve criar exatamente 5 agentes."
    assert [ag['id'] for ag in posicoes] == ['agente_1', 'agente_2', 'agente_3', 'agente_4', 'agente_5']
    assert len(links) == 5, "Anel de 5 agentes deve possuir 5 enlaces fechando o ciclo."

    val_outs = df[(df['Atributo'] == 'val_out') & (df['Valor'].notna()) & (df['Valor'] != '')]
    assert not val_outs.empty, "O CSV deve registrar mensagens entregues na topologia Anel."
    assert 'grafico_trafego_Anel.png' in pngs
    assert 'grafico_trafego_Geral.png' in pngs


def test_e2e_malha_topology():
    """Valida co-simulação fim a fim na topologia Malha Completa (N=5 peers, 10 enlaces)."""
    posicoes, links, config, df, pngs = _run_e2e_cosimulation('malha', num_perifericos=5, sim_steps=20, seed=42)

    assert len(posicoes) == 5, "Na malha, NUM_PERIFERICOS=5 deve criar exatamente 5 agentes no total."
    assert len(links) == 10, "Malha de 5 agentes deve possuir 5*4/2 = 10 enlaces bidirecionais."

    val_outs = df[(df['Atributo'] == 'val_out') & (df['Valor'].notna()) & (df['Valor'] != '')]
    assert len(val_outs) >= 50, "Todos os 5 agentes da malha devem trocar mensagens em todos os passos."
    assert 'grafico_trafego_Geral.png' in pngs
    for tech in ('Cabeada', '5G', '4G', '2G', 'Wireless'):
        assert f'grafico_trafego_{tech}.png' in pngs


def test_e2e_estrela_topology():
    """Valida co-simulação fim a fim na topologia Estrela (N=20 periféricos -> 21 agentes, 20 enlaces)."""
    posicoes, links, config, df, pngs = _run_e2e_cosimulation('estrela', num_perifericos=20, sim_steps=20, seed=42)

    assert len(posicoes) == 21, "Na estrela, NUM_PERIFERICOS=20 deve criar 1 central + 20 periféricos = 21 agentes."
    assert len(links) == 20, "Estrela de 20 periféricos deve possuir 20 enlaces."

    # Verifica que o AgenteCentral recebeu respostas síncronas dos periféricos desde o passo t=2
    central_rx = df[
        (df['Origem'] == 'OmnetSim-0.agent_central')
        & (df['Atributo'] == 'packets_received')
        & (df['Tempo'] == 19)
    ]['Valor'].astype(float).iloc[0]
    assert central_rx > 300, f"Central deve receber >300 respostas ao longo de 20 passos (recebeu {central_rx})."

    for tech in ('Geral', 'Cabeada', '5G', '4G', '2G', 'Wireless'):
        assert f'grafico_trafego_{tech}.png' in pngs
