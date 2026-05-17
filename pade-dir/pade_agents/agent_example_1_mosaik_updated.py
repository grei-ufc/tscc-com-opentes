#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from sys import argv
from twisted.internet import reactor
from pade.misc.utility import display_message, start_loop
from pade.core.agent import Agent
from pade.acl.aid import AID
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
                    # Corta as mensagens e processa-as uma a uma
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
        
        # Apenas um agente precisa de inicializar o servidor Mosaik (API)
        if self.is_sender:
            self.mosaik_sim = MosaikSim(self)

    def on_start(self):
        super().on_start()
        ACTIVE_AGENTS[self.aid.localname] = self
        display_message(self.aid.localname, '🌐 Agente Online. Ligado à Matriz OMNeT++.')
        
        if self.aid.localname == 'AgenteA':
            self.preparar_envio("Acesso autorizado. Qual é a latência da rede?", "AgenteB")

    def preparar_envio(self, conteudo, destino):
        pacote = {
            'origem': self.aid.localname,
            'destino': destino,
            'payload': conteudo
        }
        self.val_out = json.dumps(pacote)
        display_message(self.aid.localname, f"📤 Mensagem colocada na porta de saída: {self.val_out}")

    def receber_mensagem_da_rede(self, json_string):
        try:
            mensagem = json.loads(json_string)
            display_message(self.aid.localname, f"📥 PACOTE RECEBIDO DO OMNeT++!")
            display_message(self.aid.localname, f"   -> De: {mensagem['origem']} | Payload: {mensagem['payload']}")
            
            # --- LÓGICA BIDIRECIONAL CONTÍNUA ---
            
            # 1. Se eu for o Agente B e recebi do A, eu respondo
            if self.aid.localname == 'AgenteB' and mensagem['origem'] == 'AgenteA':
                self.preparar_envio("Latência processada. Sistema operante!", "AgenteA")
                
            # 2. NOVO: Se eu for o Agente A e recebi a confirmação do B, eu mando outra mensagem
            elif self.aid.localname == 'AgenteA' and mensagem['origem'] == 'AgenteB':
                self.preparar_envio("Copiado, Agente B. Mantendo a conexão ativa...", "AgenteB")
                
        except Exception:
            display_message(self.aid.localname, f"Erro ao decodificar pacote: {json_string}")

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