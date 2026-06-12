#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import zmq
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from pade.misc.utility import display_message, start_loop
from pade.core.agent import Agent
from pade.acl.aid import AID
from pade.acl.messages import ACLMessage
from pade.drivers.mosaik_driver import MosaikCon
from pade.behaviours.protocols import Behaviour, FipaRequestProtocol

MOSAIK_MODELS = {
    'api_version': '3.0',
    'type': 'time-based',
    'models': {
        'PadeAgent': {
            'public': True,
            'params': ['agent_id'],
            'attrs': [],
        },
    },
}

# Endereço do ROUTER embutido no omnet_wrapper.py (Super Wrapper).
# omnet_wrapper.py é o 'OmnetSim' do sim_config em star.py, executado
# DENTRO do container 'mosaik_master' (não em 'omnet_sim', que é só
# o binário OMNeT++/ZMQ-REP na porta 5555). Por isso o ROUTER abre
# em mosaik_master:5556 — é lá que os agentes PADE devem conectar.
ZMQ_GATEWAY_ADDR = 'tcp://mosaik_master:5556'

# ==========================================
# SERIALIZAÇÃO FIPA <-> JSON  (ponte ZMQ)
# Usada apenas pela camada de transporte.
# Os behaviours nunca tocam nessas funções.
# ==========================================

def acl_to_json(msg):
    return json.dumps({
        "performative":    msg.performative,
        "sender":          msg.sender.name if msg.sender else "Unknown",
        "receivers":       [r.name for r in msg.receivers] if msg.receivers else [],
        "content":         msg.content,
        "ontology":        msg.ontology,
        "protocol":        msg.protocol,
        "conversation_id": msg.conversation_id,
    })

def json_to_acl(json_str):
    data = json.loads(json_str)
    msg  = ACLMessage(data.get("performative"))
    sender = data.get("sender")
    if sender and sender != "Unknown":
        msg.set_sender(AID(name=sender))
    for r in data.get("receivers", []):
        msg.add_receiver(AID(name=r))
    msg.set_content(data.get("content"))
    msg.set_ontology(data.get("ontology"))
    msg.set_protocol(data.get("protocol"))
    msg.set_conversation_id(data.get("conversation_id"))
    return msg


# ==========================================
# BEHAVIOURS FIPA  (métodos nativos do protocolo — não mudam)
# ==========================================

class EnvioInicialBehaviour(Behaviour):
    """
    Disparado uma vez no on_start() do AgenteA.
    Usa self.agent.enviar_via_zmq() como transporte — a mensagem passa
    pelo gateway ZMQ → OMNeT++ e sofre latência/jitter/perda antes de
    chegar ao AgenteB. Os métodos FIPA (performative, protocol, etc.)
    permanecem intactos — só o transporte muda.
    """
    def on_start(self):
        super().on_start()
        msg = ACLMessage(ACLMessage.REQUEST)
        msg.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        msg.set_sender(self.agent.aid)
        msg.add_receiver(AID(name='AgenteB@0.0.0.0:5679'))
        msg.set_ontology('telemetria_rede')
        msg.set_conversation_id('conv-001')
        msg.set_content('Acesso autorizado. Qual é a latência da rede?')
        self.agent.enviar_via_zmq(msg)          # ponte ZMQ — transporte real
        display_message(self.agent.aid.localname, '📤 REQUEST enviado via ZMQ → OMNeT++.')

    def execute(self, message):
        pass


class ProtocoloTelemetriaB(FipaRequestProtocol):
    """
    Registrado no AgenteB.
    handle_request() é chamado automaticamente pelo PADE via react(),
    após a mensagem chegar pelo ZMQ (já com efeitos de rede aplicados)
    e ser injetada pelo LoopingCall.
    """
    def __init__(self, agent):
        super().__init__(agent=agent, message=None, is_initiator=False)

    def handle_request(self, msg):
        display_message(self.agent.aid.localname, '📥 REQUEST recebido (via OMNeT++).')
        display_message(self.agent.aid.localname,
                        f'   -> De: {msg.sender.localname} | Payload: {msg.content}')

        reply = msg.create_reply()
        reply.set_performative(ACLMessage.INFORM)
        reply.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        reply.set_content('Latência processada. Sistema operante!')
        self.agent.enviar_via_zmq(reply)        # ponte ZMQ — transporte real
        display_message(self.agent.aid.localname, '📤 INFORM enviado via ZMQ → OMNeT++.')

        self.agent.mosaik_sim.step_done()


class ProtocoloTelemetriaA(FipaRequestProtocol):
    """
    Registrado no AgenteA.
    handle_inform() é chamado automaticamente pelo PADE via react()
    após a resposta do AgenteB atravessar o OMNeT++.
    reactor.callLater garante que a simulação não trava se AgenteB
    não responder dentro do timeout.
    """
    def __init__(self, agent):
        super().__init__(agent=agent, message=None, is_initiator=True)
        self.passo_liberado = False
        self.timeout_call   = None

    def on_start(self):
        super().on_start()
        self._iniciar_timeout()

    def _iniciar_timeout(self):
        self.passo_liberado = False
        if self.timeout_call and self.timeout_call.active():
            self.timeout_call.cancel()
        self.timeout_call = reactor.callLater(2.0, self._forcar_avanco)

    def _forcar_avanco(self):
        if not self.passo_liberado:
            display_message(self.agent.aid.localname,
                            '⏰ TIMEOUT! AgenteB não respondeu. Avançando simulação.')
            self.passo_liberado = True
            self.agent.mosaik_sim.step_done()

    def handle_inform(self, msg):
        display_message(self.agent.aid.localname, '📥 INFORM recebido (via OMNeT++).')
        display_message(self.agent.aid.localname,
                        f'   -> De: {msg.sender.localname} | Payload: {msg.content}')

        if self.timeout_call and self.timeout_call.active():
            self.timeout_call.cancel()

        if not self.passo_liberado:
            nova_msg = ACLMessage(ACLMessage.REQUEST)
            nova_msg.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
            nova_msg.set_sender(self.agent.aid)
            nova_msg.add_receiver(AID(name='AgenteB@0.0.0.0:5679'))
            nova_msg.set_ontology('telemetria_rede')
            nova_msg.set_conversation_id('conv-002')
            nova_msg.set_content('Copiado, Agente B. Mantendo a conexão ativa...')
            self.agent.enviar_via_zmq(nova_msg)
            display_message(self.agent.aid.localname, '📤 Novo REQUEST enviado via ZMQ → OMNeT++.')

            self.passo_liberado = True
            self.agent.mosaik_sim.step_done()

        self._iniciar_timeout()


# ==========================================
# MOSAIK SIMULATOR
# ==========================================

class MosaikSim(MosaikCon):
    def __init__(self, agent):
        super().__init__(MOSAIK_MODELS, agent)

    def create(self, num, model, agent_id):
        return [{'eid': agent_id, 'type': model}]

    def step(self, time, inputs, max_advance=0):
        # Mosaik controla apenas o tempo — mensagens trafegam pelo ZMQ/OMNeT++
        return

    def get_data(self, outputs):
        return {}


# ==========================================
# AGENTE — placa de rede ZMQ (DEALER) integrada
# ==========================================

class AgenteFIPA(Agent):
    """
    Placa de rede ZMQ:
      - zmq.DEALER conectado ao gateway (omnet_gateway.py em omnet_sim:5556)
      - DEALER identifica-se com self.aid.name, permitindo ao ROUTER do
        gateway endereçar respostas de volta a este agente especificamente
      - LoopingCall do Twisted faz polling não bloqueante do socket,
        integrado ao reactor (sem threads)

    enviar_via_zmq(): ACLMessage → JSON → DEALER.send() → gateway

    _poll_zmq(): chamado pelo LoopingCall. Lê mensagens pendentes do
                 socket sem bloquear; cada mensagem recebida é desserializada
                 e entregue via self.react() — API NATIVA do PADE que
                 despacha para handle_request()/handle_inform() através
                 de behaviour.execute().
    """
    ZMQ_GATEWAY_ADDR = ZMQ_GATEWAY_ADDR
    ZMQ_POLL_INTERVAL = 0.05   # segundos — granularidade do polling

    def __init__(self, aid, is_sender=False):
        super().__init__(aid=aid, debug=False)
        self.is_sender = is_sender
        if self.is_sender:
            self.mosaik_sim = MosaikSim(self)

        # --- Placa de rede ZMQ ---
        self._zmq_context = zmq.Context()
        self._zmq_socket  = self._zmq_context.socket(zmq.DEALER)
        # Identidade do DEALER = nome do agente, usada pelo ROUTER do gateway
        self._zmq_socket.setsockopt_string(zmq.IDENTITY, self.aid.name)
        self._zmq_socket.setsockopt(zmq.LINGER, 0)
        self._zmq_socket.connect(self.ZMQ_GATEWAY_ADDR)

    def on_start(self):
        super().on_start()
        display_message(self.aid.localname,
                        f'🌐 Agente Online. Placa de rede ZMQ (DEALER) → {self.ZMQ_GATEWAY_ADDR}')

        # LoopingCall — integrado ao reactor, sem threads
        self._zmq_loop = LoopingCall(self._poll_zmq)
        self._zmq_loop.start(self.ZMQ_POLL_INTERVAL, now=False)

        if self.aid.localname == 'AgenteA':
            self.behaviours.append(EnvioInicialBehaviour(self))
            req_a = ProtocoloTelemetriaA(self)
            self.behaviours.append(req_a)
            req_a.on_start()

        if self.aid.localname == 'AgenteB':
            req_b = ProtocoloTelemetriaB(self)
            self.behaviours.append(req_b)
            req_b.on_start()

    def enviar_via_zmq(self, acl_msg):
        """
        Ponte de saída: ACLMessage → JSON → DEALER → gateway.
        Chamada pelos behaviours no lugar de self.agent.send().
        O gateway lê 'receivers', injeta na simulação OMNeT++ para
        calcular o delay, e entrega ao destinatário quando o tempo passar.
        """
        json_str = acl_to_json(acl_msg)
        self._zmq_socket.send_string(json_str)

    def _poll_zmq(self):
        """
        Chamado periodicamente pelo LoopingCall (não bloqueante).
        Lê todas as mensagens disponíveis no DEALER e entrega cada uma
        via self.react() — método nativo do PADE que itera
        self.behaviours e chama behaviour.execute(msg), disparando
        handle_request()/handle_inform() conforme a performativa.
        """
        try:
            while self._zmq_socket.poll(timeout=0) & zmq.POLLIN:
                json_str = self._zmq_socket.recv_string(flags=zmq.NOBLOCK)
                msg_fipa = json_to_acl(json_str)
                display_message(self.aid.localname,
                                '📬 Mensagem recebida do gateway → injetando no PADE.')
                self.react(msg_fipa)          # entrega FIPA nativa
        except zmq.Again:
            pass
        except Exception as e:
            display_message(self.aid.localname, f'⚠️ Erro polling ZMQ: {e}')


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