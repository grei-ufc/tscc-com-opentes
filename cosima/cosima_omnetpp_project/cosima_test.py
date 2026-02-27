# cosima_test.py
import socket

HOST = ''  # escuta em todas as interfaces
PORT = 4242

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"COSIMA listening on port {PORT}...")
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                data = conn.recv(1024)
                if not data:
                    continue
                print(f"Received from Mosaik: {data.decode()}")
                reply = "Acknowledged by COSIMA"
                conn.sendall(reply.encode())

if __name__ == "__main__":
    main()