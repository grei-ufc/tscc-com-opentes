"""
Adaptador Mosaik para o OMNeT++ (ZMQ Client / REQ) — SUPER WRAPPER.

PROTOCOLO CÍCLICO (Mosaik permanece o único mestre do tempo):

  init()   → conecta REQ ao MosaikBridge (porta 5555)
             abre ROUTER para os agentes PADE (porta 5556)
  create() → envia CREATE/CONNECT, recebe ACK
  step(t)  → 1. drena mensagens FIPA pendentes do ROUTER (não bloqueante)
             2. monta val_in com essas mensagens
             3. envia STEP(t, inputs+val_in, time_resolution) ao MosaikBridge
             4. recebe {status, data, mosaik_step} — data inclui val_out
             5. entrega val_out aos agentes corretos via ROUTER
             6. armazena métricas em last_results
             7. retorna t + 1
  get_data() → devolve last_results (métricas) para o Mosaik/collector

FUSÃO COM O GATEWAY:
  - Apenas ESTE módulo conversa com o MosaikBridge via REQ (porta 5555).
  - O ROUTER (porta 5556) substitui o gateway separado — fica integrado
    ao mesmo step(), eliminando a corrida REQ/REP entre dois processos.
  - val_in/val_out voltam ao META do NetworkNode (são o canal das
    mensagens FIPA), mas NÃO são conectados via world.connect() no
    star.py — são preenchidos/lidos aqui dentro, internamente.
"""

import mosaik_api_v3 as mosaik_api
import zmq
import json

META = {
    'type': 'time-based',
    'models': {
        'NetworkNode': {
            'public': True,
            'params': ['node_type'],
            'attrs': [
                # val_in/val_out voltam — mas usados apenas internamente
                # pelo wrapper (ROUTER), nunca conectados via world.connect()
                'val_in', 'val_out',
                'status', 'packets_sent',
                'packets_received', 'packets_dropped',
                'packet_sizes_out', 'latencies_out', 'jitters_out'
            ],
        },
        'Connection': {
            'public': True,
            'params': ['src', 'dest'],
            'attrs': [],
        },
    },
}

# Onde os agentes PADE (DEALER) se conectam
ROUTER_BIND_ADDR = 'tcp://0.0.0.0:5556'


class OmnetAdapter(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)

        # --- REQ: único cliente do MosaikBridge.cc (porta 5555) ---
        self.context = zmq.Context()
        self.socket  = self.context.socket(zmq.REQ)

        # --- ROUTER: substitui o gateway separado, integrado ao step() ---
        self.router = self.context.socket(zmq.ROUTER)
        self.router.bind(ROUTER_BIND_ADDR)

        self.sid     = None
        self.last_results   = {}
        self.time_resolution = 1.0

        # identity_frame (bytes) <-> nome do agente FIPA (string)
        # populado conforme os agentes enviam mensagens
        self._identidades = {}

    def init(self, sid, time_resolution, host='omnet_sim', port=5555):
        self.sid             = sid
        self.time_resolution = time_resolution
        self.socket.connect(f"tcp://{host}:{port}")
        print(f"[MOSAIK] Conectado ao OMNeT++ em tcp://{host}:{port} "
              f"(time_resolution={time_resolution}s/passo)")
        print(f"[WRAPPER] 🎧 ROUTER ZMQ escutando agentes em {ROUTER_BIND_ADDR}")
        return self.meta

    def create(self, num, model, **model_params):
        entities = []

        if model == 'Connection':
            for i in range(num):
                payload = {
                    'action': 'connect',
                    'src':    model_params['src'],
                    'dest':   model_params['dest'],
                }
                print(f"\n[MOSAIK] ---> CONNECT:\n{json.dumps(payload, indent=4)}")
                self.socket.send_json(payload)
                response = self.socket.recv_json()
                print(f"[MOSAIK] <--- CONNECT ACK:\n{json.dumps(response, indent=4)}")

                if response.get('status') == 'ok':
                    conn_id = f"conn_{model_params['src']}_{model_params['dest']}_{i}"
                    entities.append({'eid': conn_id, 'type': model})
                else:
                    print(f"[MOSAIK] ERRO ao conectar: {response.get('reason')}")
            return entities

        for i in range(num):
            eid     = f'node_{i}'
            payload = {
                'action': 'create',
                'eid':    eid,
                'params': model_params,
            }
            print(f"\n[MOSAIK] ---> CREATE:\n{json.dumps(payload, indent=4)}")
            self.socket.send_json(payload)
            response = self.socket.recv_json()
            print(f"[MOSAIK] <--- CREATE ACK:\n{json.dumps(response, indent=4)}")

            if response.get('status') == 'ok':
                entities.append({'eid': eid, 'type': model})
            else:
                print(f"[MOSAIK] ERRO ao criar {eid}: {response.get('reason')}")

        return entities

    # ------------------------------------------------------------
    # Drena o ROUTER sem bloquear: coleta todas as mensagens FIPA
    # que os agentes PADE enviaram desde o último step().
    # Registra/atualiza a identidade de cada remetente.
    # ------------------------------------------------------------
    def _drenar_router(self):
        recebidas = []
        while self.router.poll(timeout=0) & zmq.POLLIN:
            identity, payload = self.router.recv_multipart()
            try:
                msg = json.loads(payload.decode())
            except json.JSONDecodeError:
                continue

            sender = msg.get('sender', 'Unknown')
            self._identidades[sender] = identity
            recebidas.append(payload.decode())

            print(f"[WRAPPER] 📥 Mensagem recebida de: {sender} → "
                  f"receivers={msg.get('receivers')} "
                  f"performative={msg.get('performative')}")
        return recebidas

    # ------------------------------------------------------------
    # Entrega o conteúdo de val_out (string com '|||' separando
    # múltiplas mensagens) aos agentes corretos via ROUTER,
    # usando o campo 'receivers' de cada mensagem FIPA.
    # ------------------------------------------------------------
    def _entregar_val_out(self, val_out_str):
        if not val_out_str:
            return

        for fragmento in val_out_str.split('|||'):
            if not fragmento:
                continue
            try:
                msg = json.loads(fragmento)
            except json.JSONDecodeError:
                print(f"[MOSAIK] ⚠️ fragmento val_out não-JSON ignorado: {fragmento[:60]}")
                continue

            for receiver_name in msg.get('receivers', []):
                identity = self._identidades.get(receiver_name)
                if identity is None:
                    print(f"[MOSAIK] ⚠️ destinatário desconhecido: {receiver_name} "
                          f"(ainda não enviou nenhuma mensagem)")
                    continue

                self.router.send_multipart([identity, fragmento.encode()])
                print(f"[MOSAIK] 📤 entregue a {receiver_name} "
                      f"(performative={msg.get('performative')})")

    # ------------------------------------------------------------
    # step() — pulso único e atômico:
    #   ROUTER (drena) → val_in → MosaikBridge → val_out → ROUTER (entrega)
    # ------------------------------------------------------------
    def step(self, time, inputs, max_advance):
        # 1. Drena mensagens FIPA pendentes dos agentes PADE
        mensagens_fipa = self._drenar_router()

        # 2. Monta val_in para o NetworkNode — cada mensagem FIPA
        #    entra como uma "fonte" distinta; NetworkNode.cc concatena
        #    com '|||' e aplica delay/jitter/drop por mensagem.
        if mensagens_fipa:
            val_in_sources = {f'agente_{i}': m for i, m in enumerate(mensagens_fipa)}
            inputs = dict(inputs)  # não mutar o original
            inputs.setdefault('node_0', {})
            inputs['node_0'] = dict(inputs['node_0'])
            inputs['node_0']['val_in'] = val_in_sources

        # 3. Step único e atômico com o MosaikBridge
        payload = {
            'action':          'step',
            'time':            time,
            'inputs':          inputs,
            'time_resolution': self.time_resolution,
        }

        print(f"\n[MOSAIK] ---> STEP t={time}:\n{json.dumps(payload, indent=4)}")
        self.socket.send_json(payload)

        response = self.socket.recv_json()
        print(f"[MOSAIK] <--- STEP t={time} ACK (mosaik_step={response.get('mosaik_step')}):\n"
              f"{json.dumps(response, indent=4)}")

        if response.get('status') == 'ok':
            self.last_results = response.get('data', {})

            remote_step = response.get('mosaik_step', time)
            if remote_step != time:
                print(f"[MOSAIK] ⚠ DESSINCRONIZAÇÃO: Mosaik t={time}, "
                      f"OMNeT++ confirmou mosaik_step={remote_step}")

            # 4. Entrega val_out aos agentes PADE corretos via ROUTER
            node_data = self.last_results.get('node_0', {})
            self._entregar_val_out(node_data.get('val_out', ''))
        else:
            print(f"[MOSAIK] ERRO no STEP t={time}: {response.get('reason')}")

        return time + 1

    def get_data(self, outputs):
        # val_in/val_out não são expostos ao collector — apenas métricas
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr in ('val_in', 'val_out'):
                    continue
                if eid in self.last_results:
                    data[eid][attr] = self.last_results[eid].get(attr)
        return data


if __name__ == '__main__':
    mosaik_api.start_simulation(OmnetAdapter())