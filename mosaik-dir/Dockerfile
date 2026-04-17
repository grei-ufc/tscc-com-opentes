FROM python:3.10-slim

WORKDIR /app

# Instala dependências
RUN pip install mosaik mosaik-api pyzmq
# ... (início do ficheiro) ...
RUN pip install mosaik mosaik-api pyzmq mosaik-csv
# ... (resto do ficheiro) ...

# Copia os arquivos
COPY omnet_wrapper.py .
COPY main.py .

# Comando para rodar
CMD ["python", "main.py"]