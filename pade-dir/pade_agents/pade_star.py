import os
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

NUM_PERIFERICOS = int(os.environ.get('NUM_PERIFERICOS', 3))

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

class BroadcastPollingBehaviour(Behaviour):
    """
    Registrado no AgenteCentral.
    Dispara broadcast REQUEST para todos os periféricos a cada passo.
    self.agent.enviar_via_zmq() é o transporte — cada mensagem passa
    pelo gateway → OMNeT++ e sofre latência/jitter/perda individualmente
    antes de chegar a cada periférico.
    reactor.callLater garante que a simulação nunca trava.
    """
    def __init__(self, agent):
        super().__init__(agent)
        self.tempo_mosaik        = 0
        self.respostas_esperadas = NUM_PERIFERICOS
        self.respostas_recebidas = 0
        self.passo_liberado      = False
        self.timeout_call        = None

    def on_start(self):
        super().on_start()
        self._disparar_broadcast()

    def execute(self, message):
        pass                                # despacho feito pelo ProtocoloCentral

    def _disparar_broadcast(self):
        self.respostas_recebidas = 0
        self.passo_liberado      = False

        msg = ACLMessage(ACLMessage.REQUEST)
        msg.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        msg.set_sender(self.agent.aid)
        for i in range(1, NUM_PERIFERICOS + 1):
            msg.add_receiver(AID(name=f'AgenteP_{i}@0.0.0.0:{5678+i}'))
        msg.set_ontology('telemetria_rede')
        msg.set_conversation_id(f'poll-t{self.tempo_mosaik}')
        msg.set_content(f'Polling de status no passo t={self.tempo_mosaik}')
        self.agent.enviar_via_zmq(msg)      # ponte ZMQ — transporte real
        display_message(self.agent.aid.localname,
                        f'📡 BROADCAST t={self.tempo_mosaik} enviado via ZMQ → gateway.')

        if self.timeout_call and self.timeout_call.active():
            self.timeout_call.cancel()
        self.timeout_call = reactor.callLater(2.0, self._forcar_avanco_mosaik)

    def _forcar_avanco_mosaik(self):
        if not self.passo_liberado:
            display_message(self.agent.aid.localname,
                            f'⏰ TIMEOUT! Recebi {self.respostas_recebidas}/'
                            f'{self.respostas_esperadas}. Avançando simulação.')
            self.passo_liberado = True
            self.agent.mosaik_sim.step_done()


class ProtocoloPeriferico(FipaRequestProtocol):
    """
    Registrado em cada AgenteP_i.
    handle_request() é chamado automaticamente pelo PADE via react()
    após a mensagem chegar pelo gateway (já com efeitos de rede aplicados).
    Responde com INFORM via enviar_via_zmq() — transporte real.
    """
    def __init__(self, agent):
        super().__init__(agent=agent, message=None, is_initiator=False)

    def handle_request(self, msg):
        display_message(self.agent.aid.localname,
                        f'📥 Recebi {msg.conversation_id} (via OMNeT++). Respondendo!')
        reply = msg.create_reply()
        reply.set_performative(ACLMessage.INFORM)
        reply.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        reply.set_content(f'Status OK do {self.agent.aid.localname}')
        self.agent.enviar_via_zmq(reply)    # ponte ZMQ — transporte real


class ProtocoloCentral(FipaRequestProtocol):
    """
    Registrado no AgenteCentral.
    handle_inform() é chamado automaticamente pelo PADE via react()
    a cada INFORM que chega do gateway (já com efeitos de rede aplicados).
    Contabiliza respostas e libera step_done() quando todas chegam
    ou cancela o timeout se chegarem antes do prazo.
    """
    def __init__(self, agent):
        super().__init__(agent=agent, message=None, is_initiator=True)

    def handle_inform(self, msg):
        display_message(self.agent.aid.localname,
                        f'✅ Confirmação de {msg.sender.localname} '
                        f'(ref: {msg.conversation_id}) — via OMNeT++.')

        bc = self.agent._broadcast_behaviour
        bc.respostas_recebidas += 1

        if bc.respostas_recebidas >= bc.respostas_esperadas and not bc.passo_liberado:
            display_message(self.agent.aid.localname,
                            f'🎯 Sucesso Total! {bc.respostas_recebidas}/'
                            f'{bc.respostas_esperadas}. Avançando.')
            if bc.timeout_call and bc.timeout_call.active():
                bc.timeout_call.cancel()
            bc.passo_liberado = True
            self.agent.mosaik_sim.step_done()


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
        self.agent._broadcast_behaviour.tempo_mosaik = time
        self.agent._broadcast_behaviour._disparar_broadcast()
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
    ZMQ_POLL_INTERVAL = 0.05

    def __init__(self, aid, is_sender=False):
        super().__init__(aid=aid, debug=False)
        self.is_sender = is_sender
        if self.is_sender:
            self.mosaik_sim = MosaikSim(self)

        # --- Placa de rede ZMQ ---
        self._zmq_context = zmq.Context()
        self._zmq_socket  = self._zmq_context.socket(zmq.DEALER)
        self._zmq_socket.setsockopt_string(zmq.IDENTITY, self.aid.name)
        self._zmq_socket.setsockopt(zmq.LINGER, 0)
        self._zmq_socket.connect(self.ZMQ_GATEWAY_ADDR)

    def on_start(self):
        super().on_start()
        display_message(self.aid.localname,
                        f'🌐 Online na Topologia Estrela. Placa de rede ZMQ (DEALER) → {self.ZMQ_GATEWAY_ADDR}')

        self._zmq_loop = LoopingCall(self._poll_zmq)
        self._zmq_loop.start(self.ZMQ_POLL_INTERVAL, now=False)

        if self.aid.localname == 'AgenteCentral':
            self._broadcast_behaviour = BroadcastPollingBehaviour(self)
            self.behaviours.append(self._broadcast_behaviour)
            self._broadcast_behaviour.on_start()

            central_protocol = ProtocoloCentral(self)
            self.behaviours.append(central_protocol)
            central_protocol.on_start()

        if self.aid.localname.startswith('AgenteP_'):
            periferico_protocol = ProtocoloPeriferico(self)
            self.behaviours.append(periferico_protocol)
            periferico_protocol.on_start()

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