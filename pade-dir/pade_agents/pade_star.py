#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from pade.misc.utility import display_message, start_loop
from pade.core.agent import Agent
from pade.acl.aid import AID
from pade.acl.messages import ACLMessage
from pade.drivers.mosaik_driver import MosaikCon

NUM_PERIFERICOS = int(os.environ.get('NUM_PERIFERICOS', 3))

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

# --- TRADUTORES (Mantidos para conversão FIPA <-> JSON) ---
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
        # 1. Injeta mensagens recebidas do OMNeT++ no cérebro dos Agentes
        for eid, attrs in inputs.items():
            if eid in ACTIVE_AGENTS and 'val_in' in attrs:
                msg_recebida = list(attrs['val_in'].values())[0]
                if msg_recebida:
                    for msg in msg_recebida.split("|||"):
                        msg = msg.strip()
                        # Validação de sanidade: garante que a string não foi fragmentada
                        if msg and msg.startswith("{") and msg.endswith("}"):
                            ACTIVE_AGENTS[eid].receber_mensagem_da_rede(msg)
                        elif msg:
                            display_message("ALERTA", f"Mensagem fragmentada ignorada no passo {time}")

        # 2. Gatilho do Broadcast da Central
        if 'AgenteCentral' in ACTIVE_AGENTS:
            ACTIVE_AGENTS['AgenteCentral'].disparar_broadcast(time)

        return time + 1
        
    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr == 'val_out' and eid in ACTIVE_AGENTS:
                    # Removemos o "if ACTIVE_AGENTS[eid].val_out:"
                    # O Mosaik SEMPRE recebe a string (mesmo que vazia ""), 
                    # impedindo que o OMNeT++ receba "null" e crashe em C++.
                    data[eid][attr] = ACTIVE_AGENTS[eid].val_out
                    
                    # Limpa a porta de saída do agente após o Mosaik coletar os dados
                    ACTIVE_AGENTS[eid].val_out = "" 
        return data

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
        display_message(self.aid.localname, '🌐 Online (Topologia Estrela com Roteamento OMNeT++)')

    # --- MÉTODO SEQUESTRADO: O PADE agora não envia nada, tudo vai pro Mosaik ---
    def send(self, message):
        """
        Interceptador Inteligente:
        Separa o tráfego de simulação (OMNeT++) do tráfego de sistema do PADE.
        """
        if isinstance(message, ACLMessage):
            # DATA PLANE: Se a mensagem fizer parte da simulação, vai para o OMNeT++
            if message.ontology == 'telemetria_rede':
                novo_json = acl_to_json(message)
                
                # Previne a sobrescrita (Acumulador)
                if self.val_out:
                    self.val_out += "|||" + novo_json
                else:
                    self.val_out = novo_json
            
            # CONTROL PLANE: Mensagens internas do PADE (AMS/Sniffer) fluem normalmente
            else:
                super().send(message)

    def disparar_broadcast(self, tempo):
        msg = ACLMessage(ACLMessage.REQUEST)
        msg.set_sender(self.aid)
        for i in range(1, NUM_PERIFERICOS + 1):
            msg.add_receiver(AID(name=f'AgenteP_{i}@0.0.0.0:{5678+i}')) 
        msg.set_ontology('telemetria_rede')
        msg.set_conversation_id(f'poll-t{tempo}')
        msg.set_content(f'Status? t={tempo}')
        self.send(msg) 

    def receber_mensagem_da_rede(self, json_string):
        """Injeta a mensagem no motor de reação do PADE com segurança total"""
        try:
            msg = json_to_acl(json_string)
            if msg is not None:
                self.react(msg)
        except Exception as e:
            display_message(self.aid.localname, f"⚠️ Pacote corrompido ignorado: {e}")

    def react(self, message):
        # 1. ESCUDO ABSOLUTO: Se for o fantasma do PADE avisando de queda de conexão
        if message is None:
            return
            
        # 2. Com a garantia de que a mensagem existe, repassamos para o núcleo do PADE
        super().react(message)
        
        # 3. Ignora mensagens de sistema do PADE que caiam aqui por engano
        if getattr(message, 'ontology', None) != 'telemetria_rede':
            return
            
        # 4. Proteção extra: Garante que o remetente tem um nome legível
        nome_remetente = message.sender.localname if message.sender else "Desconhecido"

        # Lógica de negócio (agora 100% segura e assíncrona)
        if self.aid.localname.startswith('AgenteP_') and message.performative == ACLMessage.REQUEST:
            display_message(self.aid.localname, f"📥 Poll recebido ({message.conversation_id}).")
            reply = message.create_reply()
            reply.set_performative(ACLMessage.INFORM)
            reply.set_content(f"Status OK: {self.aid.localname}")
            reply.set_sender(self.aid)
            
            # Delay microscópico (0.1s) para não estrangular o Twisted/Mosaik com 50 respostas simultâneas
            self.call_later(0.1, self.send, reply)
                
        elif self.aid.localname == 'AgenteCentral' and message.performative == ACLMessage.INFORM:
            display_message(self.aid.localname, f"✅ Confirmação de {nome_remetente}")
if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5678 
    ams_config = {'name': host, 'port': 8000}
    
    agentes = []
    
    agente_central = AgenteFIPA(aid=AID(name=f'AgenteCentral@{host}:{port}'), is_sender=True)
    agente_central.update_ams(ams_config)
    agentes.append(agente_central)

    for i in range(1, NUM_PERIFERICOS + 1):
        agente_p = AgenteFIPA(aid=AID(name=f'AgenteP_{i}@{host}:{port+i}'), is_sender=False)
        agente_p.update_ams(ams_config)
        agentes.append(agente_p)

    start_loop(agentes)