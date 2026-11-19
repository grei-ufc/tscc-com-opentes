#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_star.py — Agentes PADE da topologia Estrela.

AgenteCentral (master, porta PADE_PORT) + NUM_PERIFERICOS periféricos
(AgenteP_1..AgenteP_N, portas PADE_PORT+1..PADE_PORT+N).

A cada passo o central faz poll (REQUEST) em todos os periféricos; cada
periférico responde (INFORM) ao central assim que recebe o poll.
"""

import os

from pade_bridge import (ACLMessage, ACTIVE_AGENTS, AgenteCosim, PORTA_BASE,
                         aid, display_message, iniciar)

NUM_PERIFERICOS = int(os.environ.get('NUM_PERIFERICOS', 3))
ONTOLOGIA = 'telemetria_rede'


class AgenteFIPA(AgenteCosim):
    ONTOLOGIAS = (ONTOLOGIA,)
    MENSAGEM_ONLINE = '🌐 Online (Topologia Estrela com Roteamento OMNeT++)'

    def ao_passo(self, tempo):
        # Só o central inicia tráfego; os periféricos respondem em react().
        central = ACTIVE_AGENTS.get('AgenteCentral')
        if central is not None:
            central.disparar_broadcast(tempo)

    def disparar_broadcast(self, tempo):
        msg = ACLMessage(ACLMessage.REQUEST)
        msg.set_sender(self.aid)
        for i in range(1, NUM_PERIFERICOS + 1):
            msg.add_receiver(aid(f'AgenteP_{i}', PORTA_BASE + i))
        msg.set_ontology(ONTOLOGIA)
        msg.set_conversation_id(f'poll-t{tempo}')
        msg.set_content(f'Status? t={tempo}')
        self.send(msg)

    def react(self, message):
        # O PADE entrega None quando uma conexão cai.
        if message is None:
            return
        super().react(message)
        if getattr(message, 'ontology', None) != ONTOLOGIA:
            return

        nome_remetente = message.sender.localname if message.sender else 'Desconhecido'
        if self.aid.localname.startswith('AgenteP_') and message.performative == ACLMessage.REQUEST:
            display_message(self.aid.localname, f'📥 Poll recebido ({message.conversation_id}).')
            reply = message.create_reply()
            reply.set_performative(ACLMessage.INFORM)
            reply.set_content(f'Status OK: {self.aid.localname}')
            reply.set_sender(self.aid)
            # Vai para val_out no mesmo passo e sai no get_data() deste passo.
            self.send(reply)
        elif self.aid.localname == 'AgenteCentral' and message.performative == ACLMessage.INFORM:
            display_message(self.aid.localname, f'✅ Confirmação de {nome_remetente}')


if __name__ == '__main__':
    agentes = [AgenteFIPA(aid('AgenteCentral', PORTA_BASE), master=True)]
    agentes += [AgenteFIPA(aid(f'AgenteP_{i}', PORTA_BASE + i))
                for i in range(1, NUM_PERIFERICOS + 1)]
    iniciar(agentes)
