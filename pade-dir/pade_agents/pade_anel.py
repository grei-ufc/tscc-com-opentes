#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_anel.py — Agentes PADE da topologia Anel bidirecional.

NUM_PERIFERICOS agentes (agente_1..agente_N) em ciclo fechado. A cada passo
cada agente envia uma notificação (INFORM) aos dois vizinhos adjacentes; o
agente_1 é o master (hospeda o MosaikSim na porta PADE_PORT).
"""

import os

from cosim.topologias import vizinhos_anel
from pade_bridge import ACLMessage, AgenteCosim, PORTA_BASE, aid, iniciar

NUM_AGENTES = int(os.environ.get('NUM_PERIFERICOS', 4))
ONTOLOGIA = 'malha_restrita'

# {agente_i: {'port', 'vizinhos': [próximo, anterior]}}; o agente_1 sabe que o
# agente_N está às suas costas. Mesma vizinhança dos enlaces de montar_anel().
CONFIG_REDE = {nome: {'port': PORTA_BASE + i, 'vizinhos': viz}
               for i, (nome, viz) in enumerate(vizinhos_anel(NUM_AGENTES).items())}


class AgenteAnelFIPA(AgenteCosim):
    ONTOLOGIAS = (ONTOLOGIA,)
    MENSAGEM_ONLINE = '🌐 Online (Topologia Anel Bidirecional com Roteamento OMNeT++)'

    def __init__(self, aid, vizinhos, master=False):
        super().__init__(aid, master=master)
        self.vizinhos = vizinhos

    def agir(self, tempo):
        msg = ACLMessage(ACLMessage.INFORM)
        msg.set_sender(self.aid)
        for vizinho in self.vizinhos:
            msg.add_receiver(aid(vizinho, CONFIG_REDE[vizinho]['port']))
        msg.set_ontology(ONTOLOGIA)
        msg.set_conversation_id(f'sync-t{tempo}')
        msg.set_content(f'Notificação P2P do {self.aid.localname} em t={tempo}')
        self.send(msg)

    def react(self, message):
        if message is None or getattr(message, 'ontology', None) != ONTOLOGIA:
            return
        super().react(message)


if __name__ == '__main__':
    iniciar([AgenteAnelFIPA(aid(nome, dados['port']), dados['vizinhos'],
                            master=(nome == 'agente_1'))
             for nome, dados in CONFIG_REDE.items()])
