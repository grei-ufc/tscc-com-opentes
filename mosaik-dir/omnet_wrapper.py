"""
Adaptador Mosaik para o OMNeT++ (ZMQ Client / REQ).

PROTOCOLO CÍCLICO:
  init()   → conecta ao OMNeT++
  create() → envia CREATE/CONNECT, recebe ACK
  step(t)  → envia STEP(t, inputs, time_resolution)
             recebe {status, data, mosaik_step}
             armazena dados em last_results
             retorna t + 1  (próximo passo)
  get_data() → devolve last_results para o Mosaik
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
                'val_in', 'val_out', 'status', 'packets_sent', 
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


class OmnetAdapter(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.context = zmq.Context()
        self.socket  = self.context.socket(zmq.REQ)
        self.sid     = None
        self.last_results   = {}
        # time_resolution é definido pelo Mosaik no init()
        self.time_resolution = 1.0

    def init(self, sid, time_resolution, host='omnet_sim', port=5555):
        self.sid             = sid
        self.time_resolution = time_resolution
        self.socket.connect(f"tcp://{host}:{port}")
        print(f"[MOSAIK] Conectado ao OMNeT++ em tcp://{host}:{port} "
              f"(time_resolution={time_resolution}s/passo)")
        return self.meta

    def create(self, num, model, **model_params):
        entities = []

        # ---- Conexões (cabos) ----
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

        # ---- Nós ----
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

    def step(self, time, inputs, max_advance):
        payload = {
            'action':          'step',
            'time':            time,
            'inputs':          inputs,
            # Propaga time_resolution para o OMNeT++ alinhar seus ticks
            'time_resolution': self.time_resolution,
        }

        print(f"\n[MOSAIK] ---> STEP t={time}:\n{json.dumps(payload, indent=4)}")
        self.socket.send_json(payload)

        response = self.socket.recv_json()
        print(f"[MOSAIK] <--- STEP t={time} ACK (mosaik_step={response.get('mosaik_step')}):\n"
              f"{json.dumps(response, indent=4)}")

        if response.get('status') == 'ok':
            self.last_results = response.get('data', {})

            # Verificação de sincronismo: o OMNeT++ deve confirmar o mesmo passo
            remote_step = response.get('mosaik_step', time)
            if remote_step != time:
                print(f"[MOSAIK] ⚠ DESSINCRONIZAÇÃO: Mosaik t={time}, "
                      f"OMNeT++ confirmou mosaik_step={remote_step}")
        else:
            print(f"[MOSAIK] ERRO no STEP t={time}: {response.get('reason')}")

        # Retorna o próximo passo — Mosaik avança 1 unidade por vez
        return time + 1

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if eid in self.last_results:
                    data[eid][attr] = self.last_results[eid].get(attr)
        return data


if __name__ == '__main__':
    mosaik_api.start_simulation(OmnetAdapter())
