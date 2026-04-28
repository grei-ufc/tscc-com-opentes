FROM omnetpp/omnetpp:u22.04-6.0

RUN apt-get update && apt-get install -y \
    libzmq5-dev \
    git \
    cmake \
    build-essential \
    nlohmann-json3-dev

# Instalando os headers C++ do ZeroMQ (cppzmq)
RUN git clone https://github.com/zeromq/cppzmq.git /tmp/cppzmq && \
    cd /tmp/cppzmq && \
    mkdir build && cd build && \
    cmake .. && make install && \
    rm -rf /tmp/cppzmq

WORKDIR /root/models