FROM ubuntu:20.04
LABEL Description="Ambiente Oficial de Co-Simulacao Smart Grid - Laiza"

ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias do sistema e Python 3.8
RUN apt-get update && apt-get install -qq -y \
    python3.8 python3.8-dev python3-pip \
    wget git build-essential bison flex perl tcl-dev tk-dev \
    libxml2-dev zlib1g-dev default-jre doxygen graphviz \
    libwebkit2gtk-4.0-37 qt5-default libqt5core5a \
    libosgearth-dev openmpi-bin libopenmpi-dev \
    xvfb libprotobuf-dev protobuf-compiler clang cmake

# CORREÇÃO: Criar um link para que 'python' aponte para 'python3.8'
RUN ln -s /usr/bin/python3.8 /usr/bin/python

# 1. Instalar OMNeT++ 5.6.2
WORKDIR /usr/omnetpp
RUN wget https://github.com/omnetpp/omnetpp/releases/download/omnetpp-5.6.2/omnetpp-5.6.2-src-linux.tgz \
    && tar -xf omnetpp-5.6.2-src-linux.tgz \
    && rm omnetpp-5.6.2-src-linux.tgz
ENV PATH="/usr/omnetpp/omnetpp-5.6.2/bin:${PATH}"
RUN cd omnetpp-5.6.2 && xvfb-run ./configure PREFER_CLANG=yes CXXFLAGS=-std=c++14 && make -j$(nproc)

# 2. Instalar INET 4.2.2
WORKDIR /root/models
RUN wget https://github.com/inet-framework/inet/releases/download/v4.2.2/inet-4.2.2-src.tgz \
    && tar -xzf inet-4.2.2-src.tgz && rm inet-4.2.2-src.tgz
WORKDIR /root/models/inet4
RUN make makefiles && make -j$(nproc)

# 3. Configurar seu Repositorio
WORKDIR /root/models
COPY . .
RUN python3.8 -m pip install --upgrade pip
RUN python3.8 -m pip install -r requirements-docker.txt

# 4. Compilar a ponte C++ (CoSima)
WORKDIR /root/models/cosima_omnetpp_project
RUN opp_makemake -f --deep -O out -I../inet4/src -L../inet4/src -linet
RUN make -j$(nproc)

WORKDIR /root/models
CMD ["/bin/bash"]
