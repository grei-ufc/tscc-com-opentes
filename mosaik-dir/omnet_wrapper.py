import mosaik_api
import zmq
import json

META = {
    'type': 'hybrid',
    'models': {
        # Representa os nós físicos na rede
        'NetworkNode': {
            'params': ['node_type'],
            'attrs': ['data_in', 'data_out', 'status'],
        },
        # Representa os cabos virtuais (topologia)
        'Connection': {
            'params': ['src', 'dest'],
            'attrs': [],
        }
    },
}

class OmnetAdapter(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.sid = None
        self.last_results = {}

    def init(self, sid, time_resolution, host='omnet_sim', port=5555):
        self.sid = sid
        self.socket.connect(f"tcp://{host}:{port}")
        print(f"[MOSAIK] Conectado ao OMNeT++ em tcp://{host}:{port}")
        return self.meta

    def create(self, num, model, **model_params):
        entities = []
        
        # --- LÓGICA PARA PASSAR CABOS (CONEXÕES) ---
        if model == 'Connection':
            for i in range(num):
                payload = {
                    'action': 'connect',
                    'src': model_params['src'],
                    'dest': model_params['dest']
                }
                print(f"\n[MOSAIK] ---> Enviando comando CONNECT:\n{json.dumps(payload, indent=4)}")
                self.socket.send_json(payload)
                response = self.socket.recv_json()
                
                print(f"[MOSAIK] <--- Resposta do OMNeT++:\n{json.dumps(response, indent=4)}")
                
                if response.get('status') == 'ok':
                    # O ID do cabo é gerado dinamicamente para manter o registo no Mosaik
                    conn_id = f"conn_{model_params['src']}_{model_params['dest']}_{i}"
                    entities.append({'eid': conn_id, 'type': model})
                else:
                    print(f"[MOSAIK] ERRO ao conectar {model_params['src']} a {model_params['dest']}: {response.get('reason')}")
            return entities

        # --- LÓGICA PARA CRIAR NÓS ---
        for i in range(num):
            eid = f'node_{i}'
            payload = {
                'action': 'create',
                'eid': eid,
                'params': model_params
            }
            
            print(f"\n[MOSAIK] ---> Enviando comando CREATE:\n{json.dumps(payload, indent=4)}")
            self.socket.send_json(payload)
            response = self.socket.recv_json()
            
            print(f"[MOSAIK] <--- Resposta do OMNeT++:\n{json.dumps(response, indent=4)}")
            
            if response.get('status') == 'ok':
                entities.append({'eid': eid, 'type': model})
            else:
                print(f"[MOSAIK] ERRO ao criar entidade {eid}: {response.get('reason')}")
        
        return entities

    def step(self, time, inputs, max_advance):
        payload = {
            'action': 'step',
            'time': time,
            'inputs': inputs
        }
        
        print(f"\n[MOSAIK] ---> Enviando comando STEP (Tempo: {time}):\n{json.dumps(payload, indent=4)}")
        self.socket.send_json(payload)
        
        response = self.socket.recv_json()
        
        print(f"[MOSAIK] <--- Resultados recebidos (Tempo: {time}):\n{json.dumps(response, indent=4)}")
        
        if response.get('status') == 'ok':
            self.last_results = response.get('data', {})
        
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