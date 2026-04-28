FROM python:3.12.11-slim

WORKDIR /app

# Instala dependências
RUN pip install mosaik==3.6.0 mosaik-api-v3==3.0.14 pyzmq==27.1.0
RUN pip install mosaik==3.6.0 mosaik-api-v3==3.0.14 pyzmq==27.1.0 mosaik-csv==2.0.1

# Copia os arquivos
COPY omnet_wrapper.py .
COPY main.py .

# Comando para rodar
CMD ["python", "main.py"]