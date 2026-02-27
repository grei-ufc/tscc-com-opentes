# mosaik_test.py
import socket
import time

COSIMA_HOST = 'cosima'  # nome do contêiner COSIMA na rede docker
COSIMA_PORT = 4242

def main():
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((COSIMA_HOST, COSIMA_PORT))
                message = "Hello from Mosaik!"
                s.sendall(message.encode())
                print(f"Sent to COSIMA: {message}")

                data = s.recv(1024)
                print(f"Received from COSIMA: {data.decode()}")

            time.sleep(5)
        except ConnectionRefusedError:
            print("COSIMA not ready yet, retrying in 3s...")
            time.sleep(3)

if __name__ == "__main__":
    main()