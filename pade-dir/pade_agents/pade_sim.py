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
            'attrs': [],          # sem val_in/val_out — mensagens trafegam pelo PADE, deu bug a atribuição dessas var
        },
    },
}

# ==========================================
# BEHAVIOURS FIPA
# ==========================================

class EnvioInicialBehaviour(Behaviour):
    """
    Disparado uma vez no on_start() do AgenteA.
    Envia o primeiro REQUEST via self.agent.send() — transporte PADE nativo.
    O step() do Mosaik retorna sem time+1 (return vazio) e só avança
    quando handle_inform() chamar self.agent.mosaik_sim.step_done().
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
        self.agent.send(msg)                          # FIPA nativo — sem val_out, sem JSON manual
        display_message(self.agent.aid.localname, ' REQUEST enviado via PADE (FIPA nativo).')

    def execute(self, message):
        pass                                          # não reage a mensagens recebidas


class ProtocoloTelemetriaB(FipaRequestProtocol):
    """
    Registrado no AgenteB.
    handle_request() é chamado automaticamente pelo PADE ao receber REQUEST.
    Após responder, chama step_done() para liberar o passo do Mosaik.
    """
    def __init__(self, agent):
        super().__init__(agent=agent, message=None, is_initiator=False)

    def handle_request(self, msg):
        display_message(self.agent.aid.localname, ' REQUEST recebido.')
        display_message(self.agent.aid.localname, f'   -> De: {msg.sender.localname} | Payload: {msg.content}')

        reply = msg.create_reply()
        reply.set_performative(ACLMessage.INFORM)
        reply.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        reply.set_content('Latência processada. Sistema operante!')
        self.agent.send(reply)                        # FIPA nativo
        display_message(self.agent.aid.localname, ' INFORM enviado via PADE (FIPA nativo).')

        self.agent.mosaik_sim.step_done()             # libera o Mosaik para avançar o passo


class ProtocoloTelemetriaA(FipaRequestProtocol):
    """
    Registrado no AgenteA.
    handle_inform() é chamado automaticamente pelo PADE ao receber INFORM.
    Envia novo REQUEST e chama step_done() para liberar o próximo passo.
    """
    def __init__(self, agent):
        super().__init__(agent=agent, message=None, is_initiator=True)

    def handle_inform(self, msg):
        display_message(self.agent.aid.localname, ' INFORM recebido.')
        display_message(self.agent.aid.localname, f'   -> De: {msg.sender.localname} | Payload: {msg.content}')

        nova_msg = ACLMessage(ACLMessage.REQUEST)
        nova_msg.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        nova_msg.set_sender(self.agent.aid)
        nova_msg.add_receiver(AID(name='AgenteB@0.0.0.0:5679'))
        nova_msg.set_ontology('telemetria_rede')
        nova_msg.set_conversation_id('conv-002')
        nova_msg.set_content('Copiado, Agente B. Mantendo a conexão ativa...')
        self.agent.send(nova_msg)                     # FIPA nativo
        display_message(self.agent.aid.localname, 'Novo REQUEST enviado via PADE (FIPA nativo).')

        self.agent.mosaik_sim.step_done()             # libera o Mosaik para avançar o passo


# ==========================================
# MOSAIK SIMULATOR
# ==========================================

class MosaikSim(MosaikCon):
    def __init__(self, agent):
        super().__init__(MOSAIK_MODELS, agent)

    def create(self, num, model, agent_id):
        return [{'eid': agent_id, 'type': model}]

    def step(self, time, inputs, max_advance=0):
        # O step não entrega mensagens manualmente nem usa val_in.
        # Mensagens trafegam pelo PADE; quando o behaviour responde,
        # step_done() é chamado e o Mosaik avança automaticamente.
        # Retorno sem valor = passo suspenso até step_done().
        return

    def get_data(self, outputs):
        # Sem val_out — dados de simulação seriam retornados aqui se necessário.
        return {}


# ==========================================
# AGENTE
# ==========================================

class AgenteFIPA(Agent):
    def __init__(self, aid, is_sender=False):
        super().__init__(aid=aid, debug=False)
        self.is_sender = is_sender
        if self.is_sender:
            self.mosaik_sim = MosaikSim(self)

    def on_start(self):
        super().on_start()
        display_message(self.aid.localname, ' Agente Online. Ligado à Matriz OMNeT++ (FIPA-ACL).')

        if self.aid.localname == 'AgenteA':
            # behaviours.append() — padrão correto do PADE (não sobrescreve a lista)
            self.behaviours.append(EnvioInicialBehaviour(self))
            req_a = ProtocoloTelemetriaA(self)
            self.behaviours.append(req_a)
            req_a.on_start()

        if self.aid.localname == 'AgenteB':
            req_b = ProtocoloTelemetriaB(self)
            self.behaviours.append(req_b)
            req_b.on_start()


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