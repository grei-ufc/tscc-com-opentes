#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_malha.py — Agentes PADE para topologia Malha Completa (Full Mesh).

Em uma malha completa, cada agente conhece e se comunica diretamente com
TODOS os outros. Não existe hierarquia — nenhum agente é "central".
A diferença fundamental em relação ao pade_star.py:
  - pade_star.py: só o AgenteCentral faz broadcast para os periféricos
  - pade_malha.py: TODOS os agentes fazem broadcast para TODOS os outros

O AgenteCentral mantém o papel de "master" apenas por hospedar
o MosaikSim (porta PADE_PORT = entrada do Mosaik). Na comunicação da
malha, ele não tem papel especial.
Semântica de NUM_PERIFERICOS na malha: número TOTAL de agentes peers N (mínimo 2),
composto por AgenteCentral + AgenteP_1..AgenteP_{N-1}.
"""

import os

from pade_bridge import ACLMessage, AgenteCosim, PORTA_BASE, aid, display_message, iniciar

NUM_PERIFERICOS = int(os.environ.get('NUM_PERIFERICOS', 3))
ONTOLOGIA = 'telemetria_rede'


def _build_registry(n):
    """
    Monta o mapa {nome: porta} de todos os N agentes da malha (total = N).
    AgenteCentral → PORTA_BASE (entrada do Mosaik)
    AgenteP_i     → PORTA_BASE + i (para i = 1 .. N-1)
    É o equivalente de uma tabela ARP: cada agente sabe onde encontrar
    todos os outros sem precisar de um servidor de nomes externo.
    """
    total = max(2, n)
    reg = {'AgenteCentral': PORTA_BASE}
    for i in range(1, total):
        reg[f'AgenteP_{i}'] = PORTA_BASE + i
    return reg


REGISTRY = _build_registry(NUM_PERIFERICOS)


class AgenteMalhaFIPA(AgenteCosim):
    ONTOLOGIAS = (ONTOLOGIA,)
    MENSAGEM_ONLINE = f'Online (Full Mesh). Fala diretamente com {len(REGISTRY) - 1} agentes.'

    def agir(self, tempo):
        """
        Cada agente envia para TODOS os outros a cada passo, sem intermediários.
        O REGISTRY é o "plano de controle" — cada agente conhece o endereço de
        todos os outros. O envio é síncrono em memória (self.val_out) para manter
        sincronismo estrito com o ciclo step(t) -> get_data() do Mosaik.
        """
        destinatarios = [(n, p) for n, p in REGISTRY.items()
                         if n != self.aid.localname]
        if not destinatarios:
            return

        msg = ACLMessage(ACLMessage.INFORM)
        msg.set_sender(self.aid)
        for nome, porta in destinatarios:
            msg.add_receiver(aid(nome, porta))
        msg.set_ontology(ONTOLOGIA)
        msg.set_conversation_id(f'malha-t{tempo}')
        msg.set_content(f'Mesh update de {self.aid.localname} em t={tempo}')
        self.send(msg)

    def react(self, message):
        if message is None:
            return
        if getattr(message, 'ontology', None) != ONTOLOGIA:
            return
        super().react(message)
        remetente = message.sender.localname if message.sender else '?'
        if message.performative == ACLMessage.INFORM:
            display_message(self.aid.localname, f'📥 Mesh: recebido de {remetente}')


if __name__ == '__main__':
    iniciar([AgenteMalhaFIPA(aid(nome, porta), master=(nome == 'AgenteCentral'))
             for nome, porta in REGISTRY.items()])
