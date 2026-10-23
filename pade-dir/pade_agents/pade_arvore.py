#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_arvore.py — Agentes PADE para topologia Árvore Radial (IEC 61850 / AMI).

Hierarquia
----------
  raiz  (subestação raiz / RTU)
    └─ sub{d}_{i}  (subestação de nível d)
         └─ con{d}_{i}  (concentrador / DCU)
              └─ med{d}_{i}  (medidor / smart-meter)

Comportamento por papel
-----------------------
• medidor  : a cada passo envia leitura de telemetria (PROPOSE) diretamente
             à RAIZ com ontologia 'arvore_telemetria'.  O OMNeT++ roteia via
             multi-salto (med→con→sub→raiz) usando a tabela BFS do AgentNode.
             Responde a POLL da raiz com CONFIRM.

• raiz     : recebe telemetrias dos medidores via multi-salto e imprime
             quantas chegaram por passo.  A cada 5 passos envia REQUEST
             (poll) a TODOS os medidores de uma só vez.

• interior : envia heartbeat INFORM aos vizinhos diretos (sub/con).
             Nenhuma lógica de aplicação extra — os pacotes de passagem
             são roteados de forma transparente pelo OMNeT++.

ENV VARS
--------
ARVORE_FANOUT   ex.: "3,2,4"  (padrão)
"""

import json
import os

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

PORTA_BASE    = 5678
ARVORE_FANOUT = os.environ.get('ARVORE_FANOUT', '3,2,4')

# Ontologias
ONT_LOCAL      = 'arvore_restrita'    # heartbeat vizinho-a-vizinho (interior)
ONT_TELEMETRIA = 'arvore_telemetria'  # leituras e polls multi-salto


# ── Construção da configuração de rede ────────────────────────────────────────

def _gerar_config_arvore(fanout_str: str) -> dict:
    """
    Calcula CONFIG_REDE = {nome: {port, vizinhos}} para toda a árvore.
    Idêntico ao estado anterior; apenas exposto aqui para referência.
    """
    fan = [int(v) for v in fanout_str.split(',')]
    prefixos = ['sub', 'con', 'med']
    config = {}
    porta_counter = [PORTA_BASE]

    def prox_porta():
        p = porta_counter[0]
        porta_counter[0] += 1
        return p

    config['raiz'] = {'port': prox_porta(), 'vizinhos': []}
    nivel_atual = ['raiz']

    for d, f in enumerate(fan):
        idx = min(d, 2)
        nivel_proximo = []
        for pai_nome in nivel_atual:
            for _ in range(f):
                nid = f"{prefixos[idx]}{d + 1}_{len(nivel_proximo)}"
                config[nid] = {'port': prox_porta(), 'vizinhos': [pai_nome]}
                config[pai_nome]['vizinhos'].append(nid)
                nivel_proximo.append(nid)
        nivel_atual = nivel_proximo

    return config


CONFIG_REDE   = _gerar_config_arvore(ARVORE_FANOUT)
MEDIDORES_IDS = [n for n in CONFIG_REDE if n.startswith('med')]


def _papel(nome: str) -> str:
    """Classifica o papel do nó: 'raiz' | 'medidor' | 'interior'."""
    if nome == 'raiz':
        return 'raiz'
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
    msg = ACLMessage(data.get('performative'))
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


# ── Agente FIPA para topologia Árvore ────────────────────────────────────────

class AgenteArvoreFIPA(Agent):
    def __init__(self, aid, vizinhos, papel, is_master=False):
        super().__init__(aid=aid, debug=False)
        self.val_out   = ''
        self.vizinhos  = vizinhos
        self.papel     = papel
        self.is_master = is_master
        # Contadores usados pela raiz
        self.telemetria_recebida  = 0   # total acumulado desde o início
        self.telemetria_no_passo  = 0   # recebidos no passo anterior (reset a cada agir)
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
        elif self.papel == 'raiz':
            self._agir_raiz(tempo)
        else:
            self._agir_interior(tempo)

    def _agir_medidor(self, tempo):
        """Envia leitura de energia diretamente à raiz (multi-salto)."""
        conteudo = json.dumps({
            'tipo':    'leitura',
            'origem':  self.aid.localname,
            'tempo':   tempo,
            'energia': round(100.0 + tempo * 0.5, 2),   # valor simulado
        })
        msg = _montar_msg(
            self.aid, ['raiz'],
            ACLMessage.PROPOSE, ONT_TELEMETRIA,
            conteudo, f'tel-{self.aid.localname}-t{tempo}',
        )
        self.send(msg)

    def _agir_raiz(self, tempo):
        """Loga chegadas do passo anterior; a cada 5 passos faz poll a todos os medidores."""
        if self.telemetria_no_passo > 0:
            print(
                f"[RAIZ t={tempo}] {self.telemetria_no_passo}/{len(MEDIDORES_IDS)} "
                f"leituras recebidas no passo anterior "
                f"(total acum.={self.telemetria_recebida})"
            )
        self.telemetria_no_passo = 0

        if tempo % 5 == 0 and MEDIDORES_IDS:
            msg = _montar_msg(
                self.aid, MEDIDORES_IDS,
                ACLMessage.REQUEST, ONT_TELEMETRIA,
                json.dumps({'tipo': 'poll', 'tempo': tempo}),
                f'poll-raiz-t{tempo}',
            )
            self.send(msg)
            print(f"[RAIZ t={tempo}] poll REQUEST enviado a {len(MEDIDORES_IDS)} medidores")

    def _agir_interior(self, tempo):
        """Heartbeat local aos vizinhos diretos (sub / con)."""
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
            if self.papel == 'raiz':
                self._raiz_receber_telemetria(message)
            elif self.papel == 'medidor':
                self._medidor_receber_poll(message)

        super().react(message)

    def _raiz_receber_telemetria(self, message):
        self.telemetria_recebida += 1
        self.telemetria_no_passo += 1
        try:
            d = json.loads(message.content)
            print(
                f"[RAIZ] leitura #{self.telemetria_recebida} "
                f"de {d.get('origem','?')}: "
                f"energia={d.get('energia','?')} t={d.get('tempo','?')}"
            )
        except Exception:
            pass

    def _medidor_receber_poll(self, message):
        """Responde ao poll da raiz com CONFIRM."""
        try:
            d = json.loads(message.content)
            if d.get('tipo') == 'poll':
                ack = _montar_msg(
                    self.aid, ['raiz'],
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
        is_master = (nome == 'raiz')

        agente = AgenteArvoreFIPA(
            aid=AID(name=f'{nome}@{host}:{porta}'),
            vizinhos=vizinhos,
            papel=papel,
            is_master=is_master,
        )
        agente.update_ams(ams_config)
        agentes.append(agente)

    start_loop(agentes)