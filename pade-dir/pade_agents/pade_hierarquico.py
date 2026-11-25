#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_hierarquico.py — Agente das topologias em camadas (árvore e híbrida).

As duas topologias têm a mesma hierarquia AMI / IEC 61850 e o mesmo
comportamento; mudam só a rede (gerada em cada script) e os nomes:

    raiz/CCO ─► subestações ─► concentradores ─► medidores

Comportamento por papel
-----------------------
• medidor  : a cada passo envia leitura de telemetria (PROPOSE) direto à raiz.
             O OMNeT++ roteia por vários saltos (med→con→sub→raiz) com a tabela
             BFS do AgentNode. Responde ao poll da raiz com CONFIRM.
• raiz     : conta as leituras recebidas e, a cada 5 passos, faz poll (REQUEST)
             em todos os medidores de uma vez.
• interior : envia heartbeat (INFORM) aos vizinhos diretos. Os pacotes de
             passagem são encaminhados pelo OMNeT++, sem lógica de aplicação.

Uso: cada script cria uma subclasse definindo RAIZ, ROTULO_RAIZ, ONT_LOCAL,
ONT_TELEMETRIA e CONFIG_REDE = config_rede(<rede de cosim.topologias>) e chama
`iniciar_rede`.
"""

import json

from cosim.topologias import vizinhos
from pade_bridge import PORTA_BASE, ACLMessage, AgenteCosim, aid, endereco, iniciar


def config_rede(rede):
    """{nome: {'port', 'vizinhos'}} a partir da rede montada por cosim.topologias.

    Os vizinhos são exatamente os enlaces do DynamicNetwork.ned (mesma rede que o
    scenario.py monta); as portas seguem a ordem dos nós a partir de PORTA_BASE.
    """
    viz = vizinhos(rede)
    return {no['id']: {'port': PORTA_BASE + i, 'vizinhos': viz[no['id']]}
            for i, no in enumerate(rede.nos)}


def papel(nome, raiz):
    """Papel do nó pelo nome: 'raiz' | 'medidor' | 'interior'."""
    if nome == raiz:
        return 'raiz'
    if nome.startswith('med'):
        return 'medidor'
    return 'interior'


class AgenteHierarquico(AgenteCosim):
    RAIZ = None            # nome do nó raiz ('raiz' na árvore, 'cco' na híbrida)
    ROTULO_RAIZ = None     # prefixo dos logs ('RAIZ', 'CCO')
    ONT_LOCAL = None       # heartbeat vizinho-a-vizinho
    ONT_TELEMETRIA = None  # leituras e polls multi-salto
    CONFIG_REDE = {}       # {nome: {'port': int, 'vizinhos': [nomes]}}

    # Árvore e híbrida sempre mantiveram a inscrição do PADE no AMS
    # (estrela, malha e anel a desligam). Preservado na refatoração.
    LIMPAR_COMPORTAMENTOS_SISTEMA = False

    def __init__(self, aid, vizinhos, papel, master=False):
        super().__init__(aid, master=master)
        self.vizinhos = vizinhos
        self.papel = papel
        self.telemetria_recebida = 0   # (raiz) total acumulado desde o início
        self.telemetria_no_passo = 0   # (raiz) recebidas desde o último agir()

    @property
    def ONTOLOGIAS(self):
        return (self.ONT_LOCAL, self.ONT_TELEMETRIA)

    @classmethod
    def medidores(cls):
        return [n for n in cls.CONFIG_REDE if n.startswith('med')]

    def _mensagem(self, destinos, performative, ontologia, conteudo, conv_id):
        """ACLMessage endereçada a nós da CONFIG_REDE."""
        msg = ACLMessage(performative)
        msg.set_sender(self.aid)
        for dest in destinos:
            msg.add_receiver(aid(dest, self.CONFIG_REDE[dest]['port']))
        msg.set_ontology(ontologia)
        msg.set_conversation_id(conv_id)
        msg.set_content(conteudo)
        return msg

    # ── Lógica por passo ──────────────────────────────────────────────────────

    def agir(self, tempo):
        if self.papel == 'medidor':
            self._agir_medidor(tempo)
        elif self.papel == 'raiz':
            self._agir_raiz(tempo)
        else:
            self._agir_interior(tempo)

    def _agir_medidor(self, tempo):
        """Envia leitura de energia diretamente à raiz (multi-salto)."""
        conteudo = json.dumps({
            'tipo':    'leitura',
            'origem':  self.aid.localname,
            'tempo':   tempo,
            'energia': round(100.0 + tempo * 0.5, 2),   # valor simulado
        })
        self.send(self._mensagem(
            [self.RAIZ], ACLMessage.PROPOSE, self.ONT_TELEMETRIA,
            conteudo, f'tel-{self.aid.localname}-t{tempo}',
        ))

    def _agir_raiz(self, tempo):
        """Loga as chegadas do passo anterior; a cada 5 passos faz poll a todos os medidores."""
        medidores = self.medidores()
        if self.telemetria_no_passo > 0:
            print(
                f"[{self.ROTULO_RAIZ} t={tempo}] {self.telemetria_no_passo}/{len(medidores)} "
                f"leituras recebidas no passo anterior "
                f"(total acum.={self.telemetria_recebida})"
            )
        self.telemetria_no_passo = 0

        if tempo % 5 == 0 and medidores:
            self.send(self._mensagem(
                medidores, ACLMessage.REQUEST, self.ONT_TELEMETRIA,
                json.dumps({'tipo': 'poll', 'tempo': tempo}),
                f'poll-{self.RAIZ}-t{tempo}',
            ))
            print(f"[{self.ROTULO_RAIZ} t={tempo}] poll REQUEST enviado a {len(medidores)} medidores")

    def _agir_interior(self, tempo):
        """Heartbeat local aos vizinhos diretos."""
        if not self.vizinhos:
            return
        self.send(self._mensagem(
            self.vizinhos, ACLMessage.INFORM, self.ONT_LOCAL,
            f'Heartbeat de {self.aid.localname} em t={tempo}',
            f'hb-{self.aid.localname}-t{tempo}',
        ))

    # ── Recepção ──────────────────────────────────────────────────────────────

    def react(self, message):
        if message is None:
            return
        ont = getattr(message, 'ontology', None)
        if ont not in self.ONTOLOGIAS:
            return

        if ont == self.ONT_TELEMETRIA:
            if self.papel == 'raiz':
                self._raiz_receber_telemetria(message)
            elif self.papel == 'medidor':
                self._medidor_receber_poll(message)

        super().react(message)

    def _raiz_receber_telemetria(self, message):
        self.telemetria_recebida += 1
        self.telemetria_no_passo += 1
        try:
            d = json.loads(message.content)
            print(
                f"[{self.ROTULO_RAIZ}] leitura #{self.telemetria_recebida} "
                f"de {d.get('origem', '?')}: "
                f"energia={d.get('energia', '?')} t={d.get('tempo', '?')}"
            )
        except Exception:
            pass

    def _medidor_receber_poll(self, message):
        """Responde ao poll da raiz com CONFIRM."""
        try:
            d = json.loads(message.content)
            if d.get('tipo') == 'poll':
                self.send(self._mensagem(
                    [self.RAIZ], ACLMessage.CONFIRM, self.ONT_TELEMETRIA,
                    json.dumps({
                        'tipo':       'ack_poll',
                        'origem':     self.aid.localname,
                        'poll_tempo': d.get('tempo'),
                    }),
                    f'ack-{self.aid.localname}',
                ))
        except Exception:
            pass


def iniciar_rede(classe_agente):
    """Cria um agente por nó de `classe_agente.CONFIG_REDE` e inicia o PADE.
    O nó raiz é o master (hospeda o MosaikSim)."""
    agentes = []
    for nome, dados in classe_agente.CONFIG_REDE.items():
        agentes.append(classe_agente(
            aid=aid(nome, dados['port']),
            vizinhos=dados['vizinhos'],
            papel=papel(nome, classe_agente.RAIZ),
            master=(nome == classe_agente.RAIZ),
        ))
    iniciar(agentes)


__all__ = ['AgenteHierarquico', 'config_rede', 'endereco', 'iniciar_rede', 'papel']
