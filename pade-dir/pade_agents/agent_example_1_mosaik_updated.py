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

# =========================================================================
# TRADUTORES INVISÍVEIS: Necessários para o tráfego físico no Mosaik/OMNeT++
# =========================================================================
def acl_to_json(acl_msg):
    # Função auxiliar para garantir que tudo seja string
    def safe_str(valor):
        if isinstance(valor, bytes):
            return valor.decode('utf-8', errors='ignore')
        return str(valor) if valor is not None else None

    msg_dict = {
        "performative": acl_msg.performative,
        "sender": acl_msg.sender.name if acl_msg.sender else "Unknown",
        "receivers": [r.name for r in acl_msg.receivers] if acl_msg.receivers else [],
        # Aplica a limpeza nos campos que podem conter bytes
        "content": safe_str(acl_msg.content),
        "ontology": safe_str(acl_msg.ontology),
        "conversation_id": safe_str(acl_msg.conversation_id)
    }
    
    try:
        return json.dumps(msg_dict)
    except Exception as e:
        display_message("ERRO TRADUTOR", f"Falha ao serializar mensagem: {e}")
        return "" # Retorna vazio para não derrubar o Mosaik

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

    def create(self, num, model, agent_id):
        return [{'eid': agent_id, 'type': model}]

    def step(self, time, inputs, max_advance=0):
        for eid, attrs in inputs.items():
            if eid in ACTIVE_AGENTS and 'val_in' in attrs:
                msg_recebida = list(attrs['val_in'].values())[0]
                if msg_recebida != "":
                    for msg in msg_recebida.split("|||"):
                        if msg:
                            ACTIVE_AGENTS[eid].receber_mensagem_da_rede(msg)
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


class AgenteComunicador(Agent):
    def __init__(self, aid, is_sender=False):
        super().__init__(aid=aid, debug=False)
        self.val_out = "" 
        self.is_sender = is_sender
        
        if self.is_sender:
            self.mosaik_sim = MosaikSim(self)

    def on_start(self):
        super().on_start()
        ACTIVE_AGENTS[self.aid.localname] = self
        display_message(self.aid.localname, '🌐 Agente Online. Ligado à Matriz OMNeT++.')
        
        if self.aid.localname == 'AgenteA':
            # Criação de mensagem usando PURAMENTE o padrão FIPA do PADE
            msg = ACLMessage(ACLMessage.REQUEST)
            msg.set_sender(self.aid)
            
            # Aqui referenciamos o destino pelo nome completo ou local
            # Neste caso, configuramos o nome exato do destino como registrado
            destino_aid = AID(name='AgenteB@0.0.0.0:5679')
            msg.add_receiver(destino_aid)
            
            msg.set_content("Acesso autorizado. Qual é a latência da rede?")
            
            # O desenvolvedor acha que está enviando pelo PADE, mas será interceptado!
            self.send(msg)

    # =========================================================================
    # LOCK-IN ARQUITETURAL: Sequestro do método de envio nativo do PADE
    # =========================================================================
    def send(self, message):
        """
        Sobrescreve o método de envio do PADE.
        Qualquer 'Behavior' ou protocolo do PADE que tentar enviar uma mensagem
        vai cair nesta armadilha e ser enviado para o Mosaik.
        """
        if isinstance(message, ACLMessage):
            # Formata invisivelmente para o Mosaik
            self.val_out = acl_to_json(message)
            display_message(self.aid.localname, f"📤 ACLMessage interceptada! Roteando para o Mosaik...")
        else:
            display_message(self.aid.localname, "ERRO: O TSCC permite apenas mensagens nativas ACLMessage.")

    def receber_mensagem_da_rede(self, json_string):
        """Injeta a mensagem no motor de reação do PADE com segurança"""
        try:
            msg = json_to_acl(json_string)
            if msg is not None:
                self.react(msg)
        except Exception as e:
            # Em vez de crashar o agente, apenas avisa que um pacote corrompido foi ignorado
            display_message(self.aid.localname, f"⚠️ Pacote corrompido do OMNeT++ descartado: {e}")

    def react(self, message):
        super().react(message)
        
        # --- BLINDAGEM CONTRA A "CHAMADA FANTASMA" DO TWISTED ---
        # Se a conexão TCP cair (connectionLost), o PADE envia message=None. Ignoramos isso.
        if message is None:
            return
            
        # Periférico: Processa o REQUEST e envia resposta
        if self.aid.localname.startswith('AgenteP_') and message.performative == ACLMessage.REQUEST:
            display_message(self.aid.localname, f"📥 Poll recebido ({message.conversation_id}).")
            reply = message.create_reply()
            reply.set_performative(ACLMessage.INFORM)
            reply.set_content(f"Status OK: {self.aid.localname}")
            reply.set_sender(self.aid)
                
        # Central: Processa as respostas
        elif self.aid.localname == 'AgenteCentral' and message.performative == ACLMessage.INFORM:
            display_message(self.aid.localname, f"✅ Confirmação de {message.sender.localname}")


if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5678 

    ams_config = {'name': host, 'port': 8000}
    
    aid_a = AID(name=f'AgenteA@{host}:{port}')
    aid_b = AID(name=f'AgenteB@{host}:{port+1}')

    agente_a = AgenteComunicador(aid=aid_a, is_sender=True)
    agente_b = AgenteComunicador(aid=aid_b, is_sender=False)

    agente_a.update_ams(ams_config)
    agente_b.update_ams(ams_config)

    start_loop([agente_a, agente_b])