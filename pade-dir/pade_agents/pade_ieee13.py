#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_ieee13.py — Agentes da rede elétrica IEEE 13 barras (co-simulation-opentes)
adaptados para o barramento Mosaik + OMNeT++ do tscc-com-opentes.

Agentes instanciados (18 nós do nodes_xy.csv):
  - agent_0      : Concentrador (Agregador dos prosumidores)
  - agent_dso    : Operador do Sistema de Distribuição (DSO)
  - agent_market : Agente Coordenador do Mercado Transativo (Decomposição Dual)
  - agent_611, agent_632, agent_633, agent_634, agent_645, agent_646,
    agent_650, agent_652, agent_660, agent_670, agent_671, agent_675,
    agent_680, agent_684, agent_692 : Agentes Prosumidores / Barras IEEE 13
"""

import json
import os
import sys
import types

from pade.misc.utility import display_message, start_loop
from pade.core.agent import Agent
from pade.acl.aid import AID
from pade.acl.messages import ACLMessage
from pade.drivers.mosaik_driver import MosaikCon

if sys.platform == 'win32' and 'fcntl' not in sys.modules:
    _fcntl = types.ModuleType('fcntl')
    _fcntl.LOCK_EX = 2
    _fcntl.LOCK_UN = 8
    _fcntl.flock = lambda *args, **kwargs: None
    sys.modules['fcntl'] = _fcntl

PORTA_BASE = int(os.environ.get('PADE_PORT', 5678))
AMS_PORT = int(os.environ.get('AMS_PORT', 8000))

# Lista oficial de nós do nodes_xy.csv (co-simulation-opentes)
PROSUMER_BUSES = [
    '611', '632', '633', '634', '645', '646', '650', '652',
    '660', '670', '671', '675', '680', '684', '692'
]

ALL_AGENT_IDS = (
    ['agent_0', 'agent_dso', 'agent_market'] +
    [f'agent_{bus}' for bus in PROSUMER_BUSES]
)

AGENT_PORTS = {aid: PORTA_BASE + idx for idx, aid in enumerate(ALL_AGENT_IDS)}

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

ACTIVE_AGENTS = {}


def acl_to_json(acl_msg):
    def safe_str(valor):
        if isinstance(valor, bytes):
            return valor.decode('utf-8', errors='ignore')
        return str(valor) if valor is not None else None

    msg_dict = {
        "performative": acl_msg.performative,
        "sender": acl_msg.sender.name if acl_msg.sender else "Unknown",
        "receivers": [r.name for r in acl_msg.receivers] if acl_msg.receivers else [],
        "content": safe_str(acl_msg.content),
        "ontology": safe_str(acl_msg.ontology),
        "conversation_id": safe_str(acl_msg.conversation_id)
    }
    try:
        return json.dumps(msg_dict)
    except Exception as e:
        display_message("ERRO TRADUTOR", f"Falha ao serializar mensagem: {e}")
        return ""


def json_to_acl(json_str):
    data = json.loads(json_str)
    msg = ACLMessage(data.get("performative"))
    sender_name = data.get("sender")
    if sender_name and sender_name != "Unknown":
        msg.set_sender(AID(name=sender_name))
    for r in data.get("receivers", []):
        msg.add_receiver(AID(name=r))
    msg.set_content(data.get("content"))
    msg.set_ontology(data.get("ontology"))
    msg.set_conversation_id(data.get("conversation_id"))
    return msg


class MosaikSim(MosaikCon):
    def __init__(self, agent):
        super().__init__(MOSAIK_MODELS, agent)

    def init(self, sid, **kwargs):
        display_message(self.agent.aid.localname, f'Mosaik conectado (sid={sid})')
        return super().init(sid, **kwargs)

    def create(self, num, model, agent_id):
        return [{'eid': agent_id, 'type': model}]

    def step(self, time, inputs, max_advance=0):
        # 1. Entrega todas as mensagens que chegaram do OMNeT++ neste passo
        for eid, attrs in inputs.items():
            if eid in ACTIVE_AGENTS and 'val_in' in attrs:
                vals = list(attrs['val_in'].values())
                msg_recebida = vals[0] if vals else ""
                if msg_recebida:
                    for msg in msg_recebida.split("|||"):
                        msg = msg.strip()
                        if msg and msg.startswith("{") and msg.endswith("}"):
                            ACTIVE_AGENTS[eid].receber_mensagem_da_rede(msg)

        # 2. A cada inicio de rodada da decomposicao dual (passo par ou multiplo de 4),
        #    o Agente Mercado (ou Concentrador) dispara os sinais de preco sombra (lambda)
        rodada = (time // 2) + 1
        if time % 2 == 0 and 'agent_0' in ACTIVE_AGENTS:
            ACTIVE_AGENTS['agent_0'].iniciar_rodada_mercado(rodada, time)

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


class AgenteIEEE13(Agent):
    def __init__(self, aid, role='prosumer', is_master=False):
        super().__init__(aid=aid, debug=False)
        self.val_out = ""
        self.role = role
        self.is_master = is_master
        self.respostas_rodada = 0
        if self.is_master:
            self.mosaik_sim = MosaikSim(self)

    def on_start(self):
        self.system_behaviours.clear()
        super().on_start()
        ACTIVE_AGENTS[self.aid.localname] = self
        display_message(self.aid.localname, f'Online na IEEE 13 ({self.role})')

    def send(self, message):
        if isinstance(message, ACLMessage):
            if message.ontology == 'telemetria_rede':
                novo_json = acl_to_json(message)
                if self.val_out:
                    self.val_out += "|||" + novo_json
                else:
                    self.val_out = novo_json
            else:
                super().send(message)

    def _aid_destino(self, target_localname):
        porta = AGENT_PORTS.get(target_localname, PORTA_BASE)
        return AID(name=f'{target_localname}@0.0.0.0:{porta}')

    def iniciar_rodada_mercado(self, rodada, tempo):
        """
        Concentrador (agent_0) publica os precos sombra lambda^k para todos os
        15 prosumidores da IEEE 13 e sincroniza com DSO (agent_dso) e Mercado (agent_market).
        Payload dimensionado (~380 bytes) conforme mensagens de 24 intervalos do pade-opentes.
        """
        msg = ACLMessage(ACLMessage.CFP)
        msg.set_sender(self.aid)
        for bus in PROSUMER_BUSES:
            msg.add_receiver(self._aid_destino(f'agent_{bus}'))
        msg.add_receiver(self._aid_destino('agent_dso'))
        msg.add_receiver(self._aid_destino('agent_market'))

        msg.set_ontology('telemetria_rede')
        msg.set_conversation_id(f'dual-round-{rodada}-t{tempo}')
        # Simula vetor de 24 intervalos de preco locacional (LMP/shadow price)
        payload = json.dumps({
            "type": "SHADOW_PRICE_CFP",
            "round": rodada,
            "step": tempo,
            "lambda_abc": [round(0.35 + 0.002 * rodada, 4)] * 24
        })
        msg.set_content(payload)
        self.send(msg)

    def receber_mensagem_da_rede(self, json_string):
        try:
            msg = json_to_acl(json_string)
            if msg is not None:
                self.react(msg)
        except Exception as e:
            display_message(self.aid.localname, f"Pacote corrompido ignorado: {e}")

    def react(self, message):
        if message is None:
            return
        super().react(message)
        if getattr(message, 'ontology', None) != 'telemetria_rede':
            return

        remetente = message.sender.localname if message.sender else "Desconhecido"

        # 1. Prosumidores (Barras IEEE 13): recebem CFP de preco e devolvem perfil de potencia (PROPOSE)
        if self.role == 'prosumer' and message.performative == ACLMessage.CFP:
            display_message(self.aid.localname, f"CFP recebido de {remetente} ({message.conversation_id})")
            reply = message.create_reply()
            reply.set_performative(ACLMessage.PROPOSE)
            reply.set_sender(self.aid)
            reply.set_content(json.dumps({
                "type": "PROSUMER_SCHEDULE",
                "bus": self.aid.localname,
                "p_kw_24h": [12.5, 10.2, 8.0, 15.4] * 6
            }))
            self.send(reply)

        # 2. DSO e Market: respondem ao Concentrador com validacao de tensao e atualizacao dual
        elif self.role in ('dso', 'market') and message.performative in (ACLMessage.CFP, ACLMessage.INFORM):
            display_message(self.aid.localname, f"Sincronizacao de rede/mercado com {remetente}")
            reply = message.create_reply()
            reply.set_performative(ACLMessage.INFORM)
            reply.set_sender(self.aid)
            reply.set_content(json.dumps({
                "type": f"{self.role.upper()}_UPDATE",
                "status": "CONVERGING",
                "v_limits_ok": True
            }))
            self.send(reply)

        # 3. Concentrador (agent_0): contabiliza programacoes recebidas dos prosumidores
        elif self.role == 'concentrator' and message.performative in (ACLMessage.PROPOSE, ACLMessage.INFORM):
            self.respostas_rodada += 1
            display_message(
                self.aid.localname,
                f"Resposta recebida de {remetente} (acumulado={self.respostas_rodada})"
            )


if __name__ == '__main__':
    host = '0.0.0.0'
    ams_config = {'name': host, 'port': AMS_PORT}
    agentes = []

    for idx, aid_name in enumerate(ALL_AGENT_IDS):
        porta = PORTA_BASE + idx
        if aid_name == 'agent_0':
            role = 'concentrator'
            is_master = True
        elif aid_name == 'agent_dso':
            role = 'dso'
            is_master = False
        elif aid_name == 'agent_market':
            role = 'market'
            is_master = False
        else:
            role = 'prosumer'
            is_master = False

        ag = AgenteIEEE13(
            aid=AID(name=f'{aid_name}@{host}:{porta}'),
            role=role,
            is_master=is_master
        )
        ag.update_ams(ams_config)
        agentes.append(ag)

    start_loop(agentes)