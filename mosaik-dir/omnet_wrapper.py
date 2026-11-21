"""
Adaptador Mosaik para o OMNeT++ (ZMQ Client / REQ).

PROTOCOLO CÍCLICO:
  init()   → guarda host/porta (NÃO envia nada: o OMNeT++ pode nem ter subido)
  create() → 1ª chamada: aguarda o OMNeT++ responder (handshake com retry),
             depois envia CREATE/CONNECT e recebe ACK
  step(t)  → envia STEP(t, inputs, time_resolution)
             recebe {status, data, mosaik_step}
             armazena dados em last_results
             retorna t + 1  (próximo passo)
  get_data() → devolve last_results para o Mosaik

Por que existe o handshake
--------------------------
O socket REQ do ZeroMQ não "descobre" o servidor: se o OMNeT++ ainda está
compilando/inicializando (ou se o host estiver errado), o primeiro recv_json()
só falha com zmq.Again depois do timeout inteiro e o socket fica preso no estado
"aguardando resposta". Aqui sondamos o servidor com uma mensagem inócua
('connect' com nós fictícios, que o MosaikBridge.cc responde sem efeito), com
um socket NOVO a cada tentativa, até ele responder ou estourar
OMNET_STARTUP_TIMEOUT_S. Se o erro persistir, a mensagem diz EXATAMENTE para
qual host:porta tentamos conectar.

Variáveis de ambiente
---------------------
OMNET_HOST               host do OMNeT++ (padrão 'omnet_sim' — nome do serviço no docker compose)
OMNET_PORT               porta (padrão 5555)
OMNET_STARTUP_TIMEOUT_S  quanto esperar o OMNeT++ subir (padrão 180 s)
OMNET_TIMEOUT_MS         timeout de cada CREATE/STEP depois do handshake (padrão 30000 ms)
"""

import json
import os
import socket
import time

import mosaik_api_v3 as mosaik_api
import zmq

META = {
    'type': 'time-based',
    'models': {
        'AgentNode': {
            'public': True,
            'params': ['node_type', 'eid'],
            'attrs': [
                'val_in', 'val_out', 'status', 'packets_sent',
                'packets_received', 'packets_dropped', 'packets_forwarded',
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

_LOOPBACK = ('127.0.0.1', 'localhost', '0.0.0.0', '::1')
_PROBE = {'action': 'connect', 'src': '_probe', 'dest': '_probe'}
_PROBE_TIMEOUT_MS = 2000


def _resolve(host):
    try:
        socket.gethostbyname(host)
        return True
    except OSError:
        return False


class OmnetAdapter(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.context = zmq.Context()
        self.socket  = None
        self.sid     = None
        self.host    = None
        self.port    = None
        self.last_results   = {}
        # time_resolution é definido pelo Mosaik no init()
        self.time_resolution = 1.0
        self.timeout_ms = int(os.environ.get('OMNET_TIMEOUT_MS', 30000))
        self.startup_timeout_s = float(os.environ.get('OMNET_STARTUP_TIMEOUT_S', 180))
        self._pronto = False

    # ── conexão ──────────────────────────────────────────────────────────
    def _novo_socket(self, host, timeout_ms):
        s = self.context.socket(zmq.REQ)
        s.setsockopt(zmq.LINGER, 0)
        s.setsockopt(zmq.RCVTIMEO, timeout_ms)
        s.setsockopt(zmq.SNDTIMEO, timeout_ms)
        s.connect(f"tcp://{host}:{self.port}")
        return s

    def _hosts_candidatos(self):
        """Host pedido primeiro. Se for loopback (127.0.0.1/localhost), o OMNeT++ de um
        container vizinho NÃO está lá: tenta também o nome do serviço 'omnet_sim'."""
        candidatos = [self.host]
        if self.host in _LOOPBACK and _resolve('omnet_sim'):
            candidatos.append('omnet_sim')
        return candidatos

    def _aguardar_omnet(self):
        """Handshake: repete a sondagem com socket novo até o OMNeT++ responder."""
        if self._pronto:
            return
        candidatos = self._hosts_candidatos()
        if len(candidatos) > 1:
            print(f"[MOSAIK] ⚠ OMNET_HOST={self.host} aponta para este próprio container; "
                  f"também vou tentar '{candidatos[1]}'.")
        inicio, tentativa, ultimo_aviso = time.time(), 0, 0.0
        while time.time() - inicio < self.startup_timeout_s:
            host = candidatos[tentativa % len(candidatos)]
            tentativa += 1
            sock = self._novo_socket(host, _PROBE_TIMEOUT_MS)
            try:
                sock.send_json(_PROBE)
                resp = sock.recv_json()
                if isinstance(resp, dict):          # qualquer resposta = servidor vivo
                    sock.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
                    sock.setsockopt(zmq.SNDTIMEO, self.timeout_ms)
                    if self.socket is not None:
                        self.socket.close(linger=0)
                    self.socket, self.host, self._pronto = sock, host, True
                    print(f"[MOSAIK] OMNeT++ respondeu em tcp://{host}:{self.port} "
                          f"(após {time.time() - inicio:.1f} s).")
                    return
            except zmq.ZMQError:
                pass
            sock.close(linger=0)
            if time.time() - ultimo_aviso > 10:
                ultimo_aviso = time.time()
                print(f"[MOSAIK] Aguardando OMNeT++ em {', '.join(f'tcp://{h}:{self.port}' for h in candidatos)} "
                      f"({time.time() - inicio:.0f}/{self.startup_timeout_s:.0f} s)...")
            time.sleep(0.5)
        raise RuntimeError(
            f"OMNeT++ não respondeu em {', '.join(f'tcp://{h}:{self.port}' for h in candidatos)} "
            f"durante {self.startup_timeout_s:.0f} s. Verifique: (1) o container omnet_sim subiu e "
            f"imprimiu 'Rede encontrada! Iniciando simulacao...' sem erro; (2) dentro do Docker o host "
            f"deve ser 'omnet_sim', NÃO 127.0.0.1 (variável OMNET_HOST); (3) a porta {self.port} é a "
            f"mesma do MosaikBridge.cc.")

    def _pedido(self, payload, rotulo):
        """send + recv com mensagem de erro clara (sem reenviar: STEP não é idempotente)."""
        try:
            self.socket.send_json(payload)
            return self.socket.recv_json()
        except zmq.Again:
            raise RuntimeError(
                f"OMNeT++ não respondeu ao {rotulo} em {self.timeout_ms} ms "
                f"(tcp://{self.host}:{self.port}). O processo pode ter travado ou encerrado; "
                f"veja o log do container omnet_sim.") from None

    # ── API do Mosaik ────────────────────────────────────────────────────
    def init(self, sid, time_resolution, host=None, port=None):
        self.sid             = sid
        self.time_resolution = time_resolution
        self.host = host or os.environ.get('OMNET_HOST', 'omnet_sim')
        self.port = int(port or os.environ.get('OMNET_PORT', 5555))
        # Só guarda o endereço: o OMNeT++ pode ainda nem ter iniciado (o scenario.py
        # costuma subir os simuladores antes de gerar o DynamicNetwork.ned).
        print(f"[MOSAIK] OMNeT++ configurado em tcp://{self.host}:{self.port} "
              f"(time_resolution={time_resolution}s/passo)")
        return self.meta

    def create(self, num, model, **model_params):
        self._aguardar_omnet()
        entities = []

        # ---- Conexões (cabos lógicos via Mosaik) ----
        if model == 'Connection':
            for i in range(num):
                payload = {
                    'action': 'connect',
                    'src':    model_params['src'],
                    'dest':   model_params['dest'],
                }
                print(f"\n[MOSAIK] ---> CONNECT:\n{json.dumps(payload, indent=4)}")
                response = self._pedido(payload, 'CONNECT')
                print(f"[MOSAIK] <--- CONNECT ACK:\n{json.dumps(response, indent=4)}")

                if response.get('status') == 'ok':
                    conn_id = f"conn_{model_params['src']}_{model_params['dest']}_{i}"
                    entities.append({'eid': conn_id, 'type': model})
                else:
                    print(f"[MOSAIK] ERRO ao conectar: {response.get('reason')}")
            return entities

        # ---- Nós (AgentNodes) ----
        for i in range(num):
            eid = model_params.get('eid', f'{model}_{i}')

            payload = {
                'action': 'create',
                'eid':    eid,
                'params': model_params,
            }
            print(f"\n[MOSAIK] ---> CREATE:\n{json.dumps(payload, indent=4)}")
            response = self._pedido(payload, f'CREATE {eid}')
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
        response = self._pedido(payload, f'STEP t={time}')
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

    def finalize(self):
        try:
            if self.socket is not None:
                self.socket.close(linger=0)
            self.context.term()
        except Exception:
            pass


if __name__ == '__main__':
    mosaik_api.start_simulation(OmnetAdapter())