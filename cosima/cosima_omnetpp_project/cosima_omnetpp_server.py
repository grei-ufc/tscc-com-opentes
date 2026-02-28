import socket
import json
from pathlib import Path
from subprocess import run
import sys

HOST = ''  # escuta em todas as interfaces do container
PORT = 4243

def run_simulation(scenario):
    """Executa o script de tutorial e devolve métricas."""
    # Ajusta variáveis do cenário, se necessário
    sim_script = '/root/models/cosima_core/scenarios/tutorial/01_simulators_and_connection_to_omnet.py'
    
    # Aqui você pode passar parâmetros via variáveis de ambiente ou arquivos temporários
    # Para simplicidade, vamos rodar o script e capturar saídas em arquivo JSON
    result_file = '/tmp/sim_metrics.json'
    
    # Supondo que o script de tutorial escreva resultados em result_file
    run(['python3', sim_script], check=True)
    
    # Lê resultados
    if Path(result_file).exists():
        with open(result_file, 'r') as f:
            return json.load(f)
    else:
        return {"error": "metrics file not found"}

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"COSIMA listening on port {PORT}...")
    
    while True:
        conn, addr = s.accept()
        print("Connected by", addr)
        data = conn.recv(4096)
        if not data:
            conn.close()
            continue

        try:
            scenario = json.loads(data.decode())
            print("Received scenario:", scenario)
            metrics = run_simulation(scenario)
        except Exception as e:
            metrics = {"error": str(e)}

        conn.sendall(json.dumps(metrics).encode())
        conn.close()

if __name__ == "__main__":
    main()