#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_malha.py — Agentes PADE para topologia Malha Completa (Full Mesh).

Em uma malha completa, cada agente conhece e se comunica diretamente com
TODOS os outros. Não existe hierarquia — nenhum agente é "central".
A diferença fundamental em relação ao pade_star.py:
  - pade_star.py: só o AgenteCentral faz broadcast para os periféricos
  - pade_malha.py: TODOS os agentes fazem broadcast para TODOS os outros

O AgenteCentral mantém o papel de "master" apenas por hospedar
o MosaikSim (porta 5678 = entrada do Mosaik). Na comunicação da
malha, ele não tem papel especial.
"""

import json
import os
from pade.misc.utility import display_message, start_loop
from pade.core.agent import Agent
from pade.acl.aid import AID
from pade.acl.messages import ACLMessage
from pade.drivers.mosaik_driver import MosaikCon

ACTIVE_AGENTS = {}

MOSAIK_MODELS = {
    'api_version': '3.0',
    'type': 'time-based',
    'models': {
        'PadeAgent': {'public': True, 'params': ['agent_id'], 'attrs': ['val_in', 'val_out']},
    },
}

NUM_PERIFERICOS = int(os.environ.get('NUM_PERIFERICOS', 3))
PORTA_BASE      = 5678


def _build_registry(n):
    """
    Monta o mapa {nome: porta} de todos os agentes da malha.
    AgenteCentral → 5678 (entrada do Mosaik)
    AgenteP_i     → 5678 + i
    É o equivalente de uma tabela ARP: cada agente sabe onde encontrar
    todos os outros sem precisar de um servidor de nomes externo.
    """
    reg = {'AgenteCentral': PORTA_BASE}
    for i in range(1, n + 1):
        reg[f'AgenteP_{i}'] = PORTA_BASE + i
    return reg


REGISTRY = _build_registry(NUM_PERIFERICOS)


def acl_to_json(acl_msg):
    def safe(v):
        if isinstance(v, bytes): return v.decode('utf-8', errors='ignore')
        return str(v) if v is not None else None
    return json.dumps({
        "performative":    acl_msg.performative,
        "sender":          acl_msg.sender.name if acl_msg.sender else "Unknown",
        "receivers":       [r.name for r in acl_msg.receivers] if acl_msg.receivers else [],
        "content":         safe(acl_msg.content),
        "ontology":        safe(acl_msg.ontology),
        "conversation_id": safe(acl_msg.conversation_id),
    })


def json_to_acl(json_str):
    data = json.loads(json_str)
    msg  = ACLMessage(data.get("performative"))
    if data.get("sender"):
        msg.set_sender(AID(name=data["sender"]))
    for r in data.get("receivers", []):
        msg.add_receiver(AID(name=r))
    msg.set_content(data.get("content"))
    msg.set_ontology(data.get("ontology"))
    msg.set_conversation_id(data.get("conversation_id"))
    return msg


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
                    for msg in raw.split("|||"):
                        msg = msg.strip()
                        if msg and msg.startswith("{") and msg.endswith("}"):
                            ACTIVE_AGENTS[eid].receber_mensagem_da_rede(msg)

        for eid, agente in ACTIVE_AGENTS.items():
            agente.agir(time)

        return time + 1

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr == 'val_out' and eid in ACTIVE_AGENTS:
                    data[eid][attr] = ACTIVE_AGENTS[eid].val_out
                    ACTIVE_AGENTS[eid].val_out = ""
        return data


class AgenteMalhaFIPA(Agent):
    def __init__(self, aid, is_master=False):
        super().__init__(aid=aid, debug=False)
        self.val_out   = ""
        self.is_master = is_master
        if self.is_master:
            self.mosaik_sim = MosaikSim(self)

    def on_start(self):
        super().on_start()
        ACTIVE_AGENTS[self.aid.localname] = self
        display_message(
            self.aid.localname,
            f'Online (Full Mesh). Fala diretamente com {len(REGISTRY)-1} agentes.'
        )

    def send(self, message):
        if isinstance(message, ACLMessage) and message.ontology == 'telemetria_rede':
            novo = acl_to_json(message)
            self.val_out = (self.val_out + "|||" + novo) if self.val_out else novo
        else:
            super().send(message)

    def agir(self, tempo):
        """
        Modelo correto da malha: cada agente envia para TODOS os outros
        a cada passo, sem intermediários. O REGISTRY é o "plano de
        controle" — cada agente conhece o endereço de todos os outros.
        call_later(0.05) distribui a carga para não sobrecarregar o
        Twisted com N*(N-1) mensagens simultâneas.
        """
        destinatarios = [(n, p) for n, p in REGISTRY.items()
                         if n != self.aid.localname]
        if not destinatarios:
            return

        def _enviar():
            msg = ACLMessage(ACLMessage.INFORM)
            msg.set_sender(self.aid)
            for nome, porta in destinatarios:
                msg.add_receiver(AID(name=f'{nome}@0.0.0.0:{porta}'))
            msg.set_ontology('telemetria_rede')
            msg.set_conversation_id(f'malha-t{tempo}')
            msg.set_content(f'Mesh update de {self.aid.localname} em t={tempo}')
            self.send(msg)

        self.call_later(0.05, _enviar)

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
        if getattr(message, 'ontology', None) != 'telemetria_rede':
            return
        super().react(message)
        remetente = message.sender.localname if message.sender else "?"
        if message.performative == ACLMessage.INFORM:
            display_message(self.aid.localname, f"📥 Mesh: recebido de {remetente}")


if __name__ == '__main__':
    host       = '0.0.0.0'
    ams_config = {'name': host, 'port': 8000}
    agentes    = []

    for nome, porta in REGISTRY.items():
        agente = AgenteMalhaFIPA(
            aid       = AID(name=f'{nome}@{host}:{porta}'),
            is_master = (nome == 'AgenteCentral'),
        )
        agente.update_ams(ams_config)
        agentes.append(agente)

    start_loop(agentes)