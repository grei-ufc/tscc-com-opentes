#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from sys import argv
from twisted.internet import reactor
from pade.misc.utility import display_message, start_loop
from pade.core.agent import Agent
from pade.acl.aid import AID
from pade.acl.messages import ACLMessage
from pade.drivers.mosaik_driver import MosaikCon

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

# ==========================================
# FUNÇÕES DE SERIALIZAÇÃO FIPA <-> MOSAIK
# ==========================================
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
    
    sender_name = data.get("sender")
    if sender_name and sender_name != "Unknown":
        msg.set_sender(AID(name=sender_name))
        
    for r in data.get("receivers", []):
        msg.add_receiver(AID(name=r))
        
    msg.set_content(data.get("content"))
    msg.set_ontology(data.get("ontology"))
    msg.set_conversation_id(data.get("conversation_id"))
    return msg

# ==========================================
# CLASSE DO MOSAIK SIMULATOR
# ==========================================
class MosaikSim(MosaikCon):
    def __init__(self, agent):
        super().__init__(MOSAIK_MODELS, agent)

    def create(self, num, model, agent_id):
        return [{'eid': agent_id, 'type': model}]

    def step(self, time, inputs, max_advance=0):
        for eid, attrs in inputs.items():
            if eid in ACTIVE_AGENTS and 'val_in' in attrs:
                msg_recebida = list(attrs['val_in'].values())[0]
                if msg_recebida != "":
                    ACTIVE_AGENTS[eid].receber_mensagem_da_rede(msg_recebida)
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

# ==========================================
# AGENTE INTELIGENTE (FIPA-ACL)
# ==========================================
class AgenteFIPA(Agent):
    def __init__(self, aid, is_sender=False):
        super().__init__(aid=aid, debug=False)
        self.val_out = "" 
        self.is_sender = is_sender
        
        if self.is_sender:
            self.mosaik_sim = MosaikSim(self)

    def on_start(self):
        super().on_start()
        ACTIVE_AGENTS[self.aid.localname] = self
        display_message(self.aid.localname, '🌐 Agente Online. Ligado à Matriz OMNeT++ (FIPA-ACL).')
        
        if self.aid.localname == 'AgenteA':
            self.preparar_envio_inicial()

    def preparar_envio_inicial(self):
        msg = ACLMessage(ACLMessage.REQUEST)
        msg.set_sender(self.aid)
        # Aponta diretamente para o endereço exato do Agente B na rede PADE
        msg.add_receiver(AID(name='AgenteB@0.0.0.0:5679')) 
        msg.set_ontology('telemetria_rede')
        msg.set_conversation_id('conv-001')
        msg.set_content('Acesso autorizado. Qual é a latência da rede?')
        
        self.val_out = acl_to_json(msg)
        display_message(self.aid.localname, "📤 REQUEST FIPA-ACL submetido ao Mosaik.")

    def receber_mensagem_da_rede(self, json_string):
        try:
            msg = json_to_acl(json_string)
            display_message(self.aid.localname, f"📥 PACOTE FIPA RECEBIDO DA REDE!")
            display_message(self.aid.localname, f"   -> Performative: {msg.performative} | Ontologia: {msg.ontology}")
            display_message(self.aid.localname, f"   -> De: {msg.sender.localname} | Payload: {msg.content}")
            
            # --- LÓGICA BIDIRECIONAL ---
            
            # 1. Agente B recebe REQUEST do A -> Responde (INFORM)
            if self.aid.localname == 'AgenteB' and msg.performative == ACLMessage.REQUEST:
                reply = msg.create_reply()
                reply.set_sender(self.aid) 
                reply.set_performative(ACLMessage.INFORM)
                reply.set_content("Latência processada. Sistema operante!")
                
                self.val_out = acl_to_json(reply)
                display_message(self.aid.localname, "📤 INFORM FIPA-ACL (Resposta) submetido.")
                
            # 2. Agente A recebe INFORM do B -> Continua o loop enviando novo REQUEST
            elif self.aid.localname == 'AgenteA' and msg.performative == ACLMessage.INFORM:
                nova_msg = ACLMessage(ACLMessage.REQUEST)
                nova_msg.set_sender(self.aid)
                nova_msg.add_receiver(AID(name='AgenteB@0.0.0.0:5679'))
                nova_msg.set_ontology('telemetria_rede')
                nova_msg.set_conversation_id('conv-002') # Novo id para continuar a interação
                nova_msg.set_content("Copiado, Agente B. Mantendo a conexão ativa...")
                
                self.val_out = acl_to_json(nova_msg)
                display_message(self.aid.localname, "📤 NOVO REQUEST FIPA-ACL submetido.")
                
        except Exception as e:
            display_message(self.aid.localname, f"Erro ao descodificar pacote: {e}")

if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5678 

    ams_config = {'name': host, 'port': 8000}
    
    aid_a = AID(name=f'AgenteA@{host}:{port}')
    aid_b = AID(name=f'AgenteB@{host}:{port+1}')

    agente_a = AgenteFIPA(aid=aid_a, is_sender=True)
    agente_b = AgenteFIPA(aid=aid_b, is_sender=False)

    agente_a.update_ams(ams_config)
    agente_b.update_ams(ams_config)

    start_loop([agente_a, agente_b])