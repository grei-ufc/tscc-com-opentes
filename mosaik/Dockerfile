# Base Ubuntu 20.04
FROM ubuntu:20.04

LABEL maintainer="rsmoura"

# Evita prompts durante instalação
ENV DEBIAN_FRONTEND=noninteractive

# Instala dependências básicas
RUN apt-get update && apt-get install -y \
    python3.8 python3.8-dev python3-pip \
    git curl wget build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Cria pasta do mosaik
WORKDIR /root/mosaik

# Copia requisitos (se houver)
# COPY requirements.txt ./
# RUN pip3 install --no-cache-dir -r requirements.txt

# Instala mosaik via pip (versão estável)
RUN pip3 install --no-cache-dir mosaik

# Expõe porta padrão para Mosaik (HTTP/REST, se necessário)
EXPOSE 5000

# Comando default
CMD ["bash"]