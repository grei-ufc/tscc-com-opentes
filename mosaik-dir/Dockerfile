FROM python:3.12.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências do orquestrador e dos dashboards científicos, travadas pelo uv
# (grupo "mosaik" do pyproject.toml), com todas as transitivas em versão exata.
# Não edite requirements.txt à mão; veja o README (seção "Gerenciamento de
# dependências") para regenerá-lo.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copia os arquivos
COPY omnet_wrapper.py .

# Comando para rodar
CMD ["python"]
