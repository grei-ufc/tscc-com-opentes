FROM python:3.12.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do orquestrador e dos dashboards científicos
RUN pip install --no-cache-dir \
    mosaik==3.6.0 \
    mosaik-api-v3==3.0.14 \
    mosaik-csv==2.0.1 \
    pyzmq==27.1.0 \
    pandas \
    matplotlib \
    plotly \
    numpy

# Copia os arquivos
COPY omnet_wrapper.py .

# Comando para rodar
CMD ["python"]
