FROM python:3.12.11-slim

WORKDIR /app

# Instala dependências
RUN pip install mosaik==3.6.0 mosaik-api-v3==3.0.14 pyzmq==27.1.0
RUN pip install mosaik==3.6.0 mosaik-api-v3==3.0.14 pyzmq==27.1.0 mosaik-csv==2.0.1

# Copia os arquivos
COPY omnet_wrapper.py .
<<<<<<< HEAD
#COPY main.py .

# Comando para rodar
CMD ["python"]
=======

# Comando para rodar
CMD ["python"]
>>>>>>> eab8773c09b4b1b17c927c2946ada7f7682a41d7
