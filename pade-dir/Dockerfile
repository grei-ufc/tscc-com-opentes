FROM python:3.12.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalação de dependências de compilação (necessárias para Twisted e PyZMQ)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Atualização de ferramentas base
RUN pip install --no-cache-dir --upgrade \
    pip==24.2 \
    setuptools==75.1.0 \
    wheel==0.44.0

# Instalação do ecossistema Mosaik e dependências do PADE
RUN pip install --no-cache-dir \
    mosaik-api-v3==3.0.14 \
    twisted==24.7.0 \
    autobahn==23.6.2 \
    pyzmq==26.0.3

# Instalação oficial do Framework PADE
RUN pip install --no-cache-dir pade-agents

# Ferramenta para monitorização e debug
RUN pip install --no-cache-dir ipython==8.26.0

# Porta padrão para comunicação entre agentes/Mosaik
EXPOSE 5678

CMD ["python3", "pade_sim.py"]