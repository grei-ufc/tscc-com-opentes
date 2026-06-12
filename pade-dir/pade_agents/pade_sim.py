#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from twisted.internet import reactor
from pade.misc.utility import display_message, start_loop
from pade.core.agent import Agent
from pade.acl.aid import AID
from pade.acl.messages import ACLMessage
from pade.drivers.mosaik_driver import MosaikCon
from pade.behaviours.protocols import Behaviour, FipaRequestProtocol

# ==========================================
# TRADUTORES INVISÍVEIS (Evitam o bug do Mosaik)
# ==========================================
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

MOSAIK_MODELS = {
    'api_version': '3.0',
    'type': 'time-based',
    'models': {
        'PadeAgent': {
            'public': True,
            'params': ['agent_id'],
            'attrs': ['val_in', 'val_out'], # Restauração obrigatória para o OMNeT++ agir
        },
    },
}

ACTIVE_AGENTS = {}

# ==========================================
# MOSAIK SIMULATOR (A Camada Física)
# ==========================================
class MosaikSim(MosaikCon):
    def __init__(self, agent):
        super().__init__(MOSAIK_MODELS, agent)

    def create(self, num, model, agent_id):
        return [{'eid': agent_id, 'type': model}]

    def step(self, time, inputs, max_advance=0):
        # Lê a porta 'val_in' alimentada pelo OMNeT++ e injeta no PADE
        for eid, attrs in inputs.items():
            if eid in ACTIVE_AGENTS and 'val_in' in attrs:
                msg_recebida = list(attrs['val_in'].values())[0]
                if msg_recebida != "":
                    for msg in msg_recebida.split("|||"):
                        if msg:
                            ACTIVE_AGENTS[eid].receber_mensagem_da_rede(msg)
        
        # O tempo avança naturalmente. O bloqueio assíncrono (step_done) 
        # não é necessário se rotearmos os dados adequadamente a cada step.
        return time + 1

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr == 'val_out' and eid in ACTIVE_AGENTS:
                    # Captura a mensagem empacotada pelo interceptador
                    data[eid][attr] = ACTIVE_AGENTS[eid].val_out
                    ACTIVE_AGENTS[eid].val_out = "" 
        return data

# ==========================================
# BEHAVIOURS FIPA (A Camada Cognitiva)
# ==========================================
class EnvioInicialBehaviour(Behaviour):
    def on_start(self):
        super().on_start()
        msg = ACLMessage(ACLMessage.REQUEST)
        msg.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        msg.set_sender(self.agent.aid)
        msg.add_receiver(AID(name='AgenteB@0.0.0.0:5679'))
        msg.set_ontology('telemetria_rede')
        msg.set_conversation_id('conv-001')
        msg.set_content('Acesso autorizado. Qual é a latência da rede?')
        
        # Chama o send(). Graças ao interceptador na classe base, 
        # essa mensagem não vai para a rede do SO, vai para o Mosaik!
        self.agent.send(msg)                          
        display_message(self.agent.aid.localname, '🧠 REQUEST processado pelo Behaviour.')

    def execute(self, message):
        pass

class ProtocoloTelemetriaB(FipaRequestProtocol):
    def __init__(self, agent):
        super().__init__(agent=agent, message=None, is_initiator=False)

    def handle_request(self, msg):
        display_message(self.agent.aid.localname, '🧠 REQUEST recebido no Behaviour.')
        display_message(self.agent.aid.localname, f'   -> De: {msg.sender.localname} | Payload: {msg.content}')

        reply = msg.create_reply()
        reply.set_performative(ACLMessage.INFORM)
        reply.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        reply.set_content('Latência processada. Sistema operante!')
        
        self.agent.send(reply)
        display_message(self.agent.aid.localname, '🧠 INFORM processado pelo Behaviour.')

class ProtocoloTelemetriaA(FipaRequestProtocol):
    def __init__(self, agent):
        super().__init__(agent=agent, message=None, is_initiator=True)

    def handle_inform(self, msg):
        display_message(self.agent.aid.localname, '🧠 INFORM recebido no Behaviour.')
        display_message(self.agent.aid.localname, f'   -> De: {msg.sender.localname} | Payload: {msg.content}')

        nova_msg = ACLMessage(ACLMessage.REQUEST)
        nova_msg.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        nova_msg.set_sender(self.agent.aid)
        nova_msg.add_receiver(AID(name='AgenteB@0.0.0.0:5679'))
        nova_msg.set_ontology('telemetria_rede')
        nova_msg.set_conversation_id('conv-002')
        nova_msg.set_content('Copiado, Agente B. Mantendo a conexão ativa...')
        
        self.agent.send(nova_msg)
        display_message(self.agent.aid.localname, '🧠 Novo REQUEST processado pelo Behaviour.')


# ==========================================
# AGENTE (A Integração Lock-in)
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
        display_message(self.aid.localname, '🌐 Agente Online. Integrado à Matriz OMNeT++.')

        if self.aid.localname == 'AgenteA':
            self.behaviours.append(EnvioInicialBehaviour(self))
            req_a = ProtocoloTelemetriaA(self)
            self.behaviours.append(req_a)
            req_a.on_start()

        if self.aid.localname == 'AgenteB':
            req_b = ProtocoloTelemetriaB(self)
            self.behaviours.append(req_b)
            req_b.on_start()

    # =========================================================
    # O SEQUESTRO: Garante a passagem pelo OMNeT++
    # =========================================================
    def send(self, message):
        """Intercepta a saída nativa dos Behaviours do PADE."""
        if isinstance(message, ACLMessage):
            # Transforma em string JSON para o Mosaik não bugar
            self.val_out = acl_to_json(message)
            display_message(self.aid.localname, f"📦 Interceptado! Mensagem na porta de saída (val_out).")
        else:
            display_message(self.aid.localname, "ERRO: O sistema só permite ACLMessage.")

    def receber_mensagem_da_rede(self, json_string):
        """Injeta a resposta do Mosaik de volta nos Behaviours."""
        try:
            msg_fipa = json_to_acl(json_string)
            # O método react() acorda automaticamente o FipaRequestProtocol!
            self.react(msg_fipa)
        except Exception as e:
            display_message(self.aid.localname, f"Erro ao decodificar pacote FIPA: {e}")

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