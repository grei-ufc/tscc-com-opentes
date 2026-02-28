#!/usr/bin/env python3
import socket
import json

HOST = '0.0.0.0'
PORT = 4242

def simulate_delay(msg_size_bytes):
    # Exemplo simples: 0.1ms por byte
    return msg_size_bytes * 0.0001  # segundos

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"DelayServer rodando em {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        with conn:
            data = conn.recv(1024)
            if not data:
                continue
            try:
                payload = json.loads(data.decode())
                size = payload.get("msg_size", 0)
                delay = simulate_delay(size)
                response = {"delay": delay}
                conn.sendall(json.dumps(response).encode())
            except Exception as e:
                conn.sendall(json.dumps({"error": str(e)}).encode())