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

# Dependências Python travadas pelo uv (grupo "pade" do pyproject.toml):
# mosaik-api-v3, twisted, autobahn, pyzmq, pade-agents e ipython, com todas
# as transitivas em versão exata. Não edite requirements.txt à mão; veja o
# README (seção "Gerenciamento de dependências") para regenerá-lo.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Porta padrão para comunicação entre agentes/Mosaik
EXPOSE 5678

CMD ["python3", "pade_sim.py"]
