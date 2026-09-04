#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
    'models': {'PadeAgent': {'public': True, 'params': ['agent_id'], 'attrs': ['val_in', 'val_out']}},
}

NUM_AGENTES = int(os.environ.get('NUM_PERIFERICOS', 4))
PORTA_BASE = 5678

# MATEMÁTICA 3: Mapeamento Lógico de Vizinhos bidirecional
# Calcula quem está à frente e quem está atrás na roda, garantindo que o Agente 1 saiba que o Agente N está nas suas costas.
def _gerar_config_rede(total_agentes):
    config = {}
    for i in range(1, total_agentes + 1):
        nome = f'agente_{i}'
        proximo = f'agente_{i % total_agentes + 1}'
        anterior = f'agente_{(i - 2) % total_agentes + 1}'
        
        # Evita duplicação caso a rede tenha apenas 2 agentes
        vizinhos = [proximo, anterior] if proximo != anterior else [proximo]
        config[nome] = {'port': PORTA_BASE + i - 1, 'vizinhos': vizinhos}
    return config

CONFIG_REDE = _gerar_config_rede(NUM_AGENTES)

def acl_to_json(acl_msg):
    msg_dict = {
        "performative": acl_msg.performative,
        "sender": acl_msg.sender.name if acl_msg.sender else "Unknown",
        "receivers": [r.name for r in acl_msg.receivers] if acl_msg.receivers else [],
        "content": acl_msg.content,
        "ontology": acl_msg.ontology,
        "conversation_id": acl_msg.conversation_id
    }
    return json.dumps(msg_dict)

def json_to_acl(json_str):
    data = json.loads(json_str)
    msg = ACLMessage(data.get("performative"))
    if data.get("sender"): msg.set_sender(AID(name=data.get("sender")))
    for r in data.get("receivers", []): msg.add_receiver(AID(name=r))
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
                msg_recebida = list(attrs['val_in'].values())[0]
                if msg_recebida:
                    for msg in msg_recebida.split("|||"):
                        msg = msg.strip()
                        if msg.startswith("{"): ACTIVE_AGENTS[eid].receber_mensagem_da_rede(msg)

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

class AgenteAnelFIPA(Agent):
    def __init__(self, aid, vizinhos, is_master=False):
        super().__init__(aid=aid, debug=False)
        self.val_out = "" 
        self.vizinhos = vizinhos 
        self.is_master = is_master
        if self.is_master:
            self.mosaik_sim = MosaikSim(self)

    def on_start(self):
        super().on_start()
        ACTIVE_AGENTS[self.aid.localname] = self

    def send(self, message):
        if isinstance(message, ACLMessage) and message.ontology == 'malha_restrita':
            novo_json = acl_to_json(message)
            if self.val_out: self.val_out += "|||" + novo_json
            else: self.val_out = novo_json
        else:
            super().send(message)

    def agir(self, tempo):
        msg = ACLMessage(ACLMessage.INFORM)
        msg.set_sender(self.aid)
        
        for vizinho in self.vizinhos:
            porta_vizinho = CONFIG_REDE[vizinho]['port']
            msg.add_receiver(AID(name=f'{vizinho}@0.0.0.0:{porta_vizinho}')) 
                
        msg.set_ontology('malha_restrita')
        msg.set_conversation_id(f'sync-t{tempo}')
        msg.set_content(f'Notificação P2P do {self.aid.localname} em t={tempo}')
        self.send(msg) 

    def receber_mensagem_da_rede(self, json_string):
        try:
            msg = json_to_acl(json_string)
            if msg is not None: self.react(msg)
        except: pass

    def react(self, message):
        if message is None or getattr(message, 'ontology', None) != 'malha_restrita': return
        super().react(message)

if __name__ == '__main__':
    host = '0.0.0.0'
    ams_config = {'name': host, 'port': 8000}
    agentes = []
    
    for nome, dados in CONFIG_REDE.items():
        porta = dados['port']
        vizinhos = dados['vizinhos']
        is_master = (nome == 'agente_1') 
        
        agente = AgenteAnelFIPA(aid=AID(name=f'{nome}@{host}:{porta}'), vizinhos=vizinhos, is_master=is_master)
        agente.update_ams(ams_config)
        agentes.append(agente)

    start_loop(agentes)