#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_hibrida.py — Agentes PADE para topologia Híbrida em camadas (IEC 61850 + AMI).

Hierarquia
----------
  cco           (Centro de Controle Operacional)
    └─ sub{i}   (Subestação — anel de fibra + estrelas celulares)
         └─ con{i}_{j}  (Concentrador / DCU — backhaul celular)
              └─ med{i}_{j}_{k} (Medidor inteligente — RF mesh parcial)

Comportamento por papel
-----------------------
• medidor  : a cada passo envia leitura de telemetria (PROPOSE) diretamente
             ao CCO com ontologia 'hibrida_telemetria'.  O OMNeT++ roteia
             via multi-salto (med→con→sub→cco) usando a tabela BFS do
             AgentNode.  Responde a POLL do CCO com CONFIRM.

• cco      : recebe telemetrias de todos os medidores via multi-salto e
             imprime quantas chegaram por passo.  A cada 5 passos envia
             REQUEST (poll) a TODOS os medidores de uma só vez.

• interior : envia heartbeat INFORM aos vizinhos diretos (sub/con).
             Os pacotes de passagem são roteados de forma transparente
             pelo OMNeT++.

IMPORTANTE: usa random.Random(SEMENTE_HIBRIDA) com a mesma sequência de
chamadas que scenario.py/_montar_hibrida() para reproduzir as posições e
os vizinhos RF mesh exatos.

ENV VARS
--------
SUBESTACOES        int  (padrão 3)
CONCENTRADORES     int  (padrão 3)  — por subestação
MEDIDORES_CLUSTER  int  (padrão 5)  — por concentrador
CELULAR_HIBRIDA    str  '2g'|'3g'|'4g'|'5g'  (padrão '4g')
SEMENTE_HIBRIDA    int  (padrão 42)
"""

import json
import math
import os
import random
from itertools import combinations

from pade.misc.utility import start_loop
from pade.core.agent import Agent
from pade.acl.aid import AID
from pade.acl.messages import ACLMessage
from pade.drivers.mosaik_driver import MosaikCon

# ── Estado global ─────────────────────────────────────────────────────────────
ACTIVE_AGENTS = {}
MOSAIK_MODELS = {
    'api_version': '3.0',
    'type': 'time-based',
    'models': {
        'PadeAgent': {
            'public': True,
            'params': ['agent_id'],
            'attrs': ['val_in', 'val_out'],
        },
    },
}

PORTA_BASE          = 5678
SUBESTACOES         = int(os.environ.get('SUBESTACOES',        3))
CONCENTRADORES      = int(os.environ.get('CONCENTRADORES',     3))
MEDIDORES_CLUSTER   = int(os.environ.get('MEDIDORES_CLUSTER',  5))
CELULAR_HIBRIDA     = os.environ.get('CELULAR_HIBRIDA', '4g').lower()
SEMENTE_HIBRIDA     = int(os.environ.get('SEMENTE_HIBRIDA',    42))

# Ontologias
ONT_LOCAL      = 'hibrida_restrita'    # heartbeat vizinho-a-vizinho (interior)
ONT_TELEMETRIA = 'hibrida_telemetria'  # leituras e polls multi-salto


# ── Helpers de geometria / malha (DEVE ser idêntico ao scenario.py) ───────────

def _ponto_no_disco(rng, cx, cy, r):
    ang = rng.uniform(0, 2 * math.pi)
    rad = r * math.sqrt(rng.random())
    return cx + rad * math.cos(ang), cy + rad * math.sin(ang)


def _calcular_malha_parcial(ids, pos, k_neigh=4, raio=60.0):
    arestas: set = set()
    for i in ids:
        candidatos = sorted(
            (j for j in ids if j != i),
            key=lambda j: math.hypot(pos[i][0] - pos[j][0], pos[i][1] - pos[j][1]),
        )
        for j in candidatos[:k_neigh]:
            d = math.hypot(pos[i][0] - pos[j][0], pos[i][1] - pos[j][1])
            if raio is None or d <= raio:
                arestas.add(tuple(sorted((i, j))))

    pai = {i: i for i in ids}

    def find(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    for a, b in arestas:
        pai[find(a)] = find(b)

    pares = sorted(
        combinations(ids, 2),
        key=lambda p: math.hypot(pos[p[0]][0] - pos[p[1]][0],
                                 pos[p[0]][1] - pos[p[1]][1]),
    )
    for a, b in pares:
        if find(a) != find(b):
            pai[find(a)] = find(b)
            arestas.add(tuple(sorted((a, b))))

    return arestas


# ── Construção da configuração de rede ────────────────────────────────────────

def _gerar_config_hibrida():
    """
    Reconstrói CONFIG_REDE espelhando exatamente scenario.py/_montar_hibrida().
    Usa a mesma semente aleatória para obter posições idênticas e, portanto,
    os mesmos vizinhos RF mesh.
    """
    rng = random.Random(SEMENTE_HIBRIDA)
    config: dict = {}
    porta_counter = [PORTA_BASE]

    def prox_porta():
        p = porta_counter[0]
        porta_counter[0] += 1
        return p

    config['cco'] = {'port': prox_porta(), 'vizinhos': []}

    subs = []
    pos_subs = {}
    for i in range(SUBESTACOES):
        ang = 2 * math.pi * i / SUBESTACOES
        sid = f'sub{i}'
        sx  = 2500 * math.cos(ang)
        sy  = 2500 * math.sin(ang)
        config[sid] = {'port': prox_porta(), 'vizinhos': []}
        subs.append(sid)
        pos_subs[sid] = (sx, sy)

    n = len(subs)
    if n >= 3:
        for i in range(n):
            a, b = subs[i], subs[(i + 1) % n]
            if b not in config[a]['vizinhos']:
                config[a]['vizinhos'].append(b)
            if a not in config[b]['vizinhos']:
                config[b]['vizinhos'].append(a)
    elif n == 2:
        config[subs[0]]['vizinhos'].append(subs[1])
        config[subs[1]]['vizinhos'].append(subs[0])

    for s in subs[:2]:
        if s not in config['cco']['vizinhos']:
            config['cco']['vizinhos'].append(s)
        if 'cco' not in config[s]['vizinhos']:
            config[s]['vizinhos'].append('cco')

    for i, sid in enumerate(subs):
        sx, sy = pos_subs[sid]
        for j in range(CONCENTRADORES):
            cid = f'con{i}_{j}'
            cx, cy = _ponto_no_disco(rng, sx, sy, 700)
            config[cid] = {'port': prox_porta(), 'vizinhos': [sid]}
            config[sid]['vizinhos'].append(cid)

            cluster = [cid]
            cluster_pos = {cid: (cx, cy)}
            for k in range(MEDIDORES_CLUSTER):
                mid = f'med{i}_{j}_{k}'
                mx, my = _ponto_no_disco(rng, cx, cy, 150.0)
                config[mid] = {'port': prox_porta(), 'vizinhos': []}
                cluster.append(mid)
                cluster_pos[mid] = (mx, my)

            for a, b in _calcular_malha_parcial(cluster, cluster_pos, k_neigh=4, raio=60.0):
                if b not in config[a]['vizinhos']:
                    config[a]['vizinhos'].append(b)
                if a not in config[b]['vizinhos']:
                    config[b]['vizinhos'].append(a)

    return config


CONFIG_REDE   = _gerar_config_hibrida()
MEDIDORES_IDS = [n for n in CONFIG_REDE if n.startswith('med')]


def _papel(nome: str) -> str:
    """Classifica o papel do nó: 'cco' | 'medidor' | 'interior'."""
    if nome == 'cco':
        return 'cco'
    if nome.startswith('med'):
        return 'medidor'
    return 'interior'


# ── Serialização ACL ──────────────────────────────────────────────────────────

def acl_to_json(acl_msg):
    return json.dumps({
        'performative':    acl_msg.performative,
        'sender':          acl_msg.sender.name if acl_msg.sender else 'Unknown',
        'receivers':       [r.name for r in acl_msg.receivers] if acl_msg.receivers else [],
        'content':         acl_msg.content,
        'ontology':        acl_msg.ontology,
        'conversation_id': acl_msg.conversation_id,
    })


def json_to_acl(json_str):
    data = json.loads(json_str)
    msg  = ACLMessage(data.get('performative'))
    if data.get('sender'):
        msg.set_sender(AID(name=data['sender']))
    for r in data.get('receivers', []):
        msg.add_receiver(AID(name=r))
    msg.set_content(data.get('content'))
    msg.set_ontology(data.get('ontology'))
    msg.set_conversation_id(data.get('conversation_id'))
    return msg


def _montar_msg(remetente_aid, destinatarios, performative, ontologia, conteudo, conv_id):
    """Constrói ACLMessage com um ou mais destinatários da CONFIG_REDE."""
    msg = ACLMessage(performative)
    msg.set_sender(remetente_aid)
    for dest in destinatarios:
        porta = CONFIG_REDE[dest]['port']
        msg.add_receiver(AID(name=f'{dest}@0.0.0.0:{porta}'))
    msg.set_ontology(ontologia)
    msg.set_conversation_id(conv_id)
    msg.set_content(conteudo)
    return msg


# ── Simulador Mosaik ──────────────────────────────────────────────────────────

class MosaikSim(MosaikCon):
    def __init__(self, agent):
        super().__init__(MOSAIK_MODELS, agent)

    def create(self, num, model, agent_id):
        return [{'eid': agent_id, 'type': model}]

    def step(self, time, inputs, max_advance=0):
        for eid, attrs in inputs.items():
            if eid in ACTIVE_AGENTS and 'val_in' in attrs:
                raw = list(attrs['val_in'].values())[0]
                if raw:
                    for part in raw.split('|||'):
                        part = part.strip()
                        if part.startswith('{'):
                            ACTIVE_AGENTS[eid].receber_mensagem_da_rede(part)
        for agente in ACTIVE_AGENTS.values():
            agente.agir(time)
        return time + 1

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr == 'val_out' and eid in ACTIVE_AGENTS:
                    data[eid][attr] = ACTIVE_AGENTS[eid].val_out
                    ACTIVE_AGENTS[eid].val_out = ''
        return data


# ── Agente FIPA para topologia Híbrida ───────────────────────────────────────

class AgenteHibridaFIPA(Agent):
    def __init__(self, aid, vizinhos, papel, is_master=False):
        super().__init__(aid=aid, debug=False)
        self.val_out   = ''
        self.vizinhos  = vizinhos
        self.papel     = papel
        self.is_master = is_master
        # Contadores usados pelo CCO
        self.telemetria_recebida  = 0
        self.telemetria_no_passo  = 0
        if self.is_master:
            self.mosaik_sim = MosaikSim(self)

    def on_start(self):
        super().on_start()
        ACTIVE_AGENTS[self.aid.localname] = self

    def send(self, message):
        """Redireciona para val_out (OMNeT++) qualquer mensagem das nossas ontologias."""
        if isinstance(message, ACLMessage) and message.ontology in (ONT_LOCAL, ONT_TELEMETRIA):
            serializado = acl_to_json(message)
            self.val_out = (self.val_out + '|||' + serializado) if self.val_out else serializado
        else:
            super().send(message)

    # ── Lógica por passo ──────────────────────────────────────────────────────

    def agir(self, tempo):
        if self.papel == 'medidor':
            self._agir_medidor(tempo)
        elif self.papel == 'cco':
            self._agir_cco(tempo)
        else:
            self._agir_interior(tempo)

    def _agir_medidor(self, tempo):
        """Envia leitura de energia diretamente ao CCO (multi-salto)."""
        conteudo = json.dumps({
            'tipo':    'leitura',
            'origem':  self.aid.localname,
            'tempo':   tempo,
            'energia': round(100.0 + tempo * 0.5, 2),
        })
        msg = _montar_msg(
            self.aid, ['cco'],
            ACLMessage.PROPOSE, ONT_TELEMETRIA,
            conteudo, f'tel-{self.aid.localname}-t{tempo}',
        )
        self.send(msg)

    def _agir_cco(self, tempo):
        """Loga chegadas do passo anterior; a cada 5 passos faz poll a todos os medidores."""
        if self.telemetria_no_passo > 0:
            print(
                f"[CCO t={tempo}] {self.telemetria_no_passo}/{len(MEDIDORES_IDS)} "
                f"leituras recebidas no passo anterior "
                f"(total acum.={self.telemetria_recebida})"
            )
        self.telemetria_no_passo = 0

        if tempo % 5 == 0 and MEDIDORES_IDS:
            msg = _montar_msg(
                self.aid, MEDIDORES_IDS,
                ACLMessage.REQUEST, ONT_TELEMETRIA,
                json.dumps({'tipo': 'poll', 'tempo': tempo}),
                f'poll-cco-t{tempo}',
            )
            self.send(msg)
            print(f"[CCO t={tempo}] poll REQUEST enviado a {len(MEDIDORES_IDS)} medidores")

    def _agir_interior(self, tempo):
        """Heartbeat local aos vizinhos diretos (sub / con)."""
        if not self.vizinhos:
            return
        msg = _montar_msg(
            self.aid, self.vizinhos,
            ACLMessage.INFORM, ONT_LOCAL,
            f'Heartbeat de {self.aid.localname} em t={tempo}',
            f'hb-{self.aid.localname}-t{tempo}',
        )
        self.send(msg)

    # ── Recepção ──────────────────────────────────────────────────────────────

    def receber_mensagem_da_rede(self, json_string):
        try:
            msg = json_to_acl(json_string)
            if msg is not None:
                self.react(msg)
        except Exception:
            pass

    def react(self, message):
        if message is None:
            return
        ont = getattr(message, 'ontology', None)
        if ont not in (ONT_LOCAL, ONT_TELEMETRIA):
            return

        if ont == ONT_TELEMETRIA:
            if self.papel == 'cco':
                self._cco_receber_telemetria(message)
            elif self.papel == 'medidor':
                self._medidor_receber_poll(message)

        super().react(message)

    def _cco_receber_telemetria(self, message):
        self.telemetria_recebida += 1
        self.telemetria_no_passo += 1
        try:
            d = json.loads(message.content)
            print(
                f"[CCO] leitura #{self.telemetria_recebida} "
                f"de {d.get('origem','?')}: "
                f"energia={d.get('energia','?')} t={d.get('tempo','?')}"
            )
        except Exception:
            pass

    def _medidor_receber_poll(self, message):
        """Responde ao poll do CCO com CONFIRM."""
        try:
            d = json.loads(message.content)
            if d.get('tipo') == 'poll':
                ack = _montar_msg(
                    self.aid, ['cco'],
                    ACLMessage.CONFIRM, ONT_TELEMETRIA,
                    json.dumps({
                        'tipo':       'ack_poll',
                        'origem':     self.aid.localname,
                        'poll_tempo': d.get('tempo'),
                    }),
                    f'ack-{self.aid.localname}',
                )
                self.send(ack)
        except Exception:
            pass


# ── Ponto de entrada ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    host       = '0.0.0.0'
    ams_config = {'name': host, 'port': 8000}
    agentes    = []

    for nome, dados in CONFIG_REDE.items():
        porta     = dados['port']
        vizinhos  = dados['vizinhos']
        papel     = _papel(nome)
        is_master = (nome == 'cco')

        agente = AgenteHibridaFIPA(
            aid=AID(name=f'{nome}@{host}:{porta}'),
            vizinhos=vizinhos,
            papel=papel,
            is_master=is_master,
        )
        agente.update_ams(ams_config)
        agentes.append(agente)

    start_loop(agentes)