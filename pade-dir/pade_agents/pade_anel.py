#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_anel.py — Agentes PADE da topologia Anel bidirecional.

NUM_PERIFERICOS agentes (agente_1..agente_N) em ciclo fechado. A cada passo
cada agente envia uma notificação (INFORM) aos dois vizinhos adjacentes; o
agente_1 é o master (hospeda o MosaikSim na porta PADE_PORT).
"""

import os

from pade_bridge import ACLMessage, AgenteCosim, PORTA_BASE, aid, iniciar

NUM_AGENTES = int(os.environ.get('NUM_PERIFERICOS', 4))
ONTOLOGIA = 'malha_restrita'


def _gerar_config_rede(total_agentes):
    """Vizinhos de cada agente no anel: o próximo e o anterior, de modo que o
    agente_1 saiba que o agente_N está às suas costas."""
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
