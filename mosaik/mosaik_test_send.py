# mosaik_client_send.py
import socket
import json
import time

COSIMA_HOST = 'cosima'  # Nome do container COSIMA na rede cosima-net
COSIMA_PORT = 4243

def send_scenario(scenario):
    """Envia o cenário para o COSIMA e recebe métricas"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print(f"Conectando ao COSIMA em {COSIMA_HOST}:{COSIMA_PORT} ...")
        s.connect((COSIMA_HOST, COSIMA_PORT))
        # Envia cenário em JSON
        scenario_json = json.dumps(scenario)
        s.sendall(scenario_json.encode())

        # Recebe resposta (métricas)
        data = s.recv(4096)
        if not data:
            raise ValueError("Nenhuma resposta recebida do COSIMA")
        metrics = json.loads(data.decode())
        return metrics

if __name__ == "__main__":
    # Exemplo de cenário: o Mosaik gera e envia para COSIMA
    scenario = {
        'num_agents': 2,
        'message_size': 512
    }

    try:
        metrics = send_scenario(scenario)
        print("Métricas recebidas do COSIMA:")
        print(json.dumps(metrics, indent=2))
    except Exception as e:
        print(f"Erro na comunicação com COSIMA: {e}")