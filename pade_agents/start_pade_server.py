import threading
import asyncio
import mosaik_api_v3
from twisted.internet import reactor
from pade.acl.aid import AID  

# Dicionário global para a ponte encontrar os agentes que estão rodando
ACTIVE_AGENTS = {}

class PadeCustomDriver(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__({
            'type': 'time-based',
            'models': {
                'Agent': {
                    'public': True,
                    'params': ['agent_id'],
                    'attrs': ['val_in', 'val_out'],
                }
            }
        })

    def init(self, sid, time_resolution):
        return self.meta

    def create(self, num, model, agent_id):
        return [{'eid': agent_id, 'type': model}]

    def step(self, time, inputs, max_advance):
        for agent_id, attrs in inputs.items():
            if agent_id in ACTIVE_AGENTS and 'msg_in' in attrs:
                val = list(attrs['msg_in'].values())[0]
                ACTIVE_AGENTS[agent_id].msg_in = val
        return time + 1

    def get_data(self, outputs):
        data = {}
        for agent_id, attrs in outputs.items():
            data[agent_id] = {}
            for attr in attrs:
                if agent_id in ACTIVE_AGENTS:
                    data[agent_id][attr] = getattr(ACTIVE_AGENTS[agent_id], attr, "")
        return data

def run_mosaik_server():
    print("[PADE-SERVER] Iniciando a Ponte Mosaik na porta 5678 como Servidor...")
    sim = PadeCustomDriver()
    
    # A Mágica: Usa a função nativa do mosaik-api-v3 (>=3.0.14) para forçar o modo Servidor
    coro = mosaik_api_v3.run_as_server(sim, host='0.0.0.0', port=5678)
    
    # Como é uma função assíncrona, rodamos com o asyncio na nossa Thread
    asyncio.run(coro)

if __name__ == '__main__':
    from agent_a import AgenteA
    from agent_b import AgenteB
    
    # 1. Cria as identidades formais FIPA-ACL
    aid_a = AID(name='AgenteA@localhost:8000')
    aid_b = AID(name='AgenteB@localhost:8001')
    
    # 2. Instancia os Agentes
    agente_a = AgenteA(aid=aid_a)
    agente_b = AgenteB(aid=aid_b)
    
    # 3. Registra os agentes para o Mosaik
    ACTIVE_AGENTS['AgenteA'] = agente_a
    ACTIVE_AGENTS['AgenteB'] = agente_b
    
    # 4. Roda o Servidor Mosaik numa Thread separada
    threading.Thread(target=run_mosaik_server, daemon=True).start()
    
    # 5. Inicia o motor principal do PADE
    print("[PADE-SERVER] Iniciando os Agentes PADE...")
    reactor.run()