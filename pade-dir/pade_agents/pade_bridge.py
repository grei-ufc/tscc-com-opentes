#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pade_bridge.py — Infraestrutura comum aos agentes PADE da co-simulação.

Reúne o que antes era copiado em cada pade_<topologia>.py:

  - configuração por variáveis de ambiente (PADE_PORT, AMS_PORT)
  - substituto de fcntl para rodar no Windows (testes locais)
  - modelo Mosaik `PadeAgent` (val_in / val_out) e o simulador `MosaikSim`
  - tradução FIPA-ACL <-> JSON, o formato que trafega pelo OMNeT++
  - `AgenteCosim`: agente base que desvia o plano de dados para `val_out`

Cada script de topologia define só o comportamento dos agentes (o que cada
um envia em `agir()` e como reage em `react()`).
"""

import json
import os
import sys
import types

from pade.misc.utility import display_message, start_loop
from pade.core.agent import Agent
from pade.acl.aid import AID
from pade.acl.messages import ACLMessage
from pade.drivers.mosaik_driver import MosaikCon

# O data_logger do PADE importa fcntl (só existe em Unix). No Windows (testes locais)
# usa um substituto inócuo, instalado DEPOIS dos imports acima: se o Twisted o
# encontrar ao ser importado, passa a usar o caminho POSIX e quebra.
if sys.platform == 'win32' and 'fcntl' not in sys.modules:
    _fcntl = types.ModuleType('fcntl')
    _fcntl.LOCK_EX = 2
    _fcntl.LOCK_UN = 8
    _fcntl.flock = lambda *args, **kwargs: None
    sys.modules['fcntl'] = _fcntl

__all__ = [
    'ACLMessage', 'AID', 'ACTIVE_AGENTS', 'AMS_PORT', 'AgenteCosim', 'HOST',
    'PORTA_BASE', 'acl_to_json', 'aid', 'display_message', 'endereco',
    'iniciar', 'json_to_acl',
]

# ══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════

HOST       = '0.0.0.0'
PORTA_BASE = int(os.environ.get('PADE_PORT', 5678))   # porta do 1º agente (entrada do Mosaik)
AMS_PORT   = int(os.environ.get('AMS_PORT', 8000))
SEPARADOR  = '|||'   # separa várias mensagens JSON num mesmo val_in / val_out

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

# Agentes ativos neste processo, por nome local (ex.: 'AgenteCentral', 'agente_1').
ACTIVE_AGENTS = {}


def endereco(nome, porta):
    """Endereço FIPA de um agente deste processo: 'nome@0.0.0.0:porta'."""
    return f'{nome}@{HOST}:{porta}'


def aid(nome, porta):
    return AID(name=endereco(nome, porta))


# ══════════════════════════════════════════════════════════════
# TRADUÇÃO FIPA-ACL <-> JSON
# ══════════════════════════════════════════════════════════════

def _texto(valor):
    if isinstance(valor, bytes):
        return valor.decode('utf-8', errors='ignore')
    return str(valor) if valor is not None else None


def acl_to_json(acl_msg):
    """Serializa uma ACLMessage para o JSON que o AgentNode.cc roteia pelos `receivers`.
    Retorna None se a mensagem não puder ser serializada."""
    try:
        return json.dumps({
            'performative':    acl_msg.performative,
            'sender':          acl_msg.sender.name if acl_msg.sender else 'Unknown',
            'receivers':       [r.name for r in acl_msg.receivers] if acl_msg.receivers else [],
            'content':         _texto(acl_msg.content),
            'ontology':        _texto(acl_msg.ontology),
            'conversation_id': _texto(acl_msg.conversation_id),
        })
    except Exception as e:
        display_message('ERRO TRADUTOR', f'Falha ao serializar mensagem: {e}')
        return None


def json_to_acl(json_str):
    data = json.loads(json_str)
    msg = ACLMessage(data.get('performative'))
    remetente = data.get('sender')
    if remetente and remetente != 'Unknown':
        msg.set_sender(AID(name=remetente))
    for r in data.get('receivers', []):
        msg.add_receiver(AID(name=r))
    msg.set_content(data.get('content'))
    msg.set_ontology(data.get('ontology'))
    msg.set_conversation_id(data.get('conversation_id'))
    return msg


def _mensagens_recebidas(val_in, tempo):
    """Separa o val_in vindo do OMNeT++ em mensagens JSON completas."""
    valores = list(val_in.values()) if isinstance(val_in, dict) else [val_in]
    bruto = valores[0] if valores else ''
    mensagens = []
    for parte in (bruto or '').split(SEPARADOR):
        parte = parte.strip()
        if parte.startswith('{') and parte.endswith('}'):
            mensagens.append(parte)
        elif parte:
            display_message('ALERTA', f'Mensagem fragmentada ignorada no passo {tempo}')
    return mensagens


# ══════════════════════════════════════════════════════════════
# SIMULADOR MOSAIK
# ══════════════════════════════════════════════════════════════

class MosaikSim(MosaikCon):
    """Expõe os agentes ao Mosaik. Fica no agente "master" (o da PORTA_BASE).

    A cada passo: entrega aos agentes as mensagens que chegaram pelo OMNeT++,
    chama `master.ao_passo(t)` e devolve o `val_out` de cada agente em get_data().
    """

    def __init__(self, agent):
        super().__init__(MOSAIK_MODELS, agent)

    def init(self, sid, **kwargs):
        display_message(self.agent.aid.localname, f'🔗 Mosaik conectado (sid={sid})')
        return super().init(sid, **kwargs)

    def create(self, num, model, agent_id):
        return [{'eid': agent_id, 'type': model}]

    def step(self, time, inputs, max_advance=0):
        for eid, attrs in inputs.items():
            agente = ACTIVE_AGENTS.get(eid)
            if agente is None or 'val_in' not in attrs:
                continue
            for msg in _mensagens_recebidas(attrs['val_in'], time):
                agente.receber_mensagem_da_rede(msg)
        self.agent.ao_passo(time)
        return time + 1

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr == 'val_out' and eid in ACTIVE_AGENTS:
                    # Sempre devolve string (mesmo vazia): o OMNeT++ não aceita null.
                    data[eid][attr] = ACTIVE_AGENTS[eid].val_out
                    ACTIVE_AGENTS[eid].val_out = ''
        return data


# ══════════════════════════════════════════════════════════════
# AGENTE BASE
# ══════════════════════════════════════════════════════════════

class AgenteCosim(Agent):
    """Agente PADE cujo tráfego de simulação passa pelo OMNeT++.

    Subclasses definem:
      ONTOLOGIAS   ontologias do plano de dados: mensagens com elas vão para
                   `val_out` (e daí para o OMNeT++) em vez da rede do PADE
      agir(t)      o que o agente envia a cada passo
      react(msg)   como reage ao que recebe
    """

    ONTOLOGIAS = ()
    # Remove os comportamentos de sistema do PADE (conexão/inscrição no AMS),
    # que não participam da co-simulação.
    LIMPAR_COMPORTAMENTOS_SISTEMA = True
    MENSAGEM_ONLINE = None

    def __init__(self, aid, master=False):
        super().__init__(aid=aid, debug=False)
        self.val_out = ''
        self.is_master = master
        if master:
            self.mosaik_sim = MosaikSim(self)

    def on_start(self):
        if self.LIMPAR_COMPORTAMENTOS_SISTEMA:
            self.system_behaviours.clear()
        super().on_start()
        ACTIVE_AGENTS[self.aid.localname] = self
        if self.MENSAGEM_ONLINE:
            display_message(self.aid.localname, self.MENSAGEM_ONLINE)

    def send(self, message):
        """Plano de dados (ONTOLOGIAS) vai para val_out; o resto segue pela rede do PADE."""
        if isinstance(message, ACLMessage) and message.ontology in self.ONTOLOGIAS:
            serializado = acl_to_json(message)
            if serializado:
                self.val_out = (self.val_out + SEPARADOR + serializado) if self.val_out else serializado
        else:
            super().send(message)

    def receber_mensagem_da_rede(self, json_string):
        """Injeta no motor de reação do PADE uma mensagem entregue pelo OMNeT++."""
        try:
            msg = json_to_acl(json_string)
            if msg is not None:
                self.react(msg)
        except Exception as e:
            display_message(self.aid.localname, f'⚠️ Pacote corrompido ignorado: {e}')

    def ao_passo(self, tempo):
        """Chamado no agente master uma vez por passo do Mosaik. Padrão: todos agem."""
        for agente in ACTIVE_AGENTS.values():
            agente.agir(tempo)

    def agir(self, tempo):
        pass


def iniciar(agentes):
    """Registra os agentes no AMS e inicia o loop do Twisted."""
    ams_config = {'name': HOST, 'port': AMS_PORT}
    for agente in agentes:
        agente.update_ams(ams_config)
    start_loop(agentes)
