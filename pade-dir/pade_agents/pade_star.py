import json
import os
from twisted.internet import reactor
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

class MosaikSim(MosaikCon):
    def __init__(self, agent):
        super().__init__(MOSAIK_MODELS, agent)
        
    def create(self, num, model, agent_id):
        return [{'eid': agent_id, 'type': model}]
        
    def step(self, time, inputs, max_advance=0):
        # 1. Processa qualquer mensagem que chegue
        for eid, attrs in inputs.items():
            if eid in ACTIVE_AGENTS and 'val_in' in attrs:
                msg_recebida = list(attrs['val_in'].values())[0]
                if msg_recebida != "":
                    for msg in msg_recebida.split("|||"):
                        if msg:
                            ACTIVE_AGENTS[eid].receber_mensagem_da_rede(msg)

        # 2. Central dispara novo Broadcast independentemente do que aconteceu antes
        if 'AgenteCentral' in ACTIVE_AGENTS:
            ACTIVE_AGENTS['AgenteCentral'].enviar_broadcast_continuo(time)

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
        display_message(self.aid.localname, '🌐 Online na Topologia Estrela (Modo Polling Resiliente)')

    def enviar_broadcast_continuo(self, tempo_mosaik):
        msg = ACLMessage(ACLMessage.REQUEST)
        msg.set_sender(self.aid)
        
        for i in range(1, NUM_PERIFERICOS + 1):
            msg.add_receiver(AID(name=f'AgenteP_{i}@0.0.0.0:{5678+i}')) 
        
        msg.set_ontology('telemetria_rede')
        msg.set_conversation_id(f'poll-t{tempo_mosaik}') # Marca o tempo na mensagem
        msg.set_content(f'Polling de status no passo t={tempo_mosaik}')
        
        self.val_out = acl_to_json(msg)
        display_message(self.aid.localname, f"📡 BROADCAST t={tempo_mosaik} enviado. Aguardando quem puder responder...")

    def receber_mensagem_da_rede(self, json_string):
        try:
            msg = json_to_acl(json_string)
            sou_destinatario = any(r.name == self.aid.name for r in msg.receivers)
            if not sou_destinatario and msg.sender.name != self.aid.name:
                return 
            
            # Periférico recebe o Broadcast e TENTA RESPONDER
            if self.aid.localname.startswith('AgenteP_') and msg.performative == ACLMessage.REQUEST:
                display_message(self.aid.localname, f"📥 Recebi pacote {msg.conversation_id}. Enviando resposta!")
                reply = msg.create_reply()
                reply.set_sender(self.aid)
                reply.set_performative(ACLMessage.INFORM)
                reply.set_content(f"Status OK do {self.aid.localname}")
                self.val_out = acl_to_json(reply)
                
            # Central recebe as respostas
            elif self.aid.localname == 'AgenteCentral' and msg.performative == ACLMessage.INFORM:
                display_message(self.aid.localname, f"✅ Confirmação recebida de {msg.sender.localname} (ref: {msg.conversation_id})")
                
        except Exception:
            pass

if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5678 
    ams_config = {'name': host, 'port': 8000}
    
    agentes = []
    
    aid_central = AID(name=f'AgenteCentral@{host}:{port}')
    agente_central = AgenteFIPA(aid=aid_central, is_sender=True)
    agente_central.update_ams(ams_config)
    agentes.append(agente_central)

    for i in range(1, NUM_PERIFERICOS + 1):
        aid_p = AID(name=f'AgenteP_{i}@{host}:{port+i}')
        agente_p = AgenteFIPA(aid=aid_p, is_sender=False)
        agente_p.update_ams(ams_config)
        agentes.append(agente_p)

    start_loop(agentes)