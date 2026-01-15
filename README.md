# tscc-com-opentes

Repositório para armazenar soluções de **simulação de comunicação**.

Neste projeto, o simulador de comunicação adotado é o **OMNeT++** e a integração com o **Mosaik** é feita via **CoSima**. Este README documenta um fluxo **reprodutível** para clonar o CoSima e executar o **Tutorial 01** usando **Docker** (modo `cmd`) e, opcionalmente, com **interface gráfica** (`gui`) no **WSL/Windows**.

---

## Sumário

- [Visão geral](#visão-geral)
- [Pré-requisitos](#pré-requisitos)
- [Quickstart (modo cmd)](#quickstart-modo-cmd)
- [Executar o Tutorial 01](#executar-o-tutorial-01)
- [Troubleshooting](#troubleshooting)
- [Rodar com interface gráfica no WSL (modo gui)](#rodar-com-interface-gráfica-no-wsl-modo-gui)

---

## Visão geral

O fluxo abaixo utiliza:
- **Docker** para construir e executar um ambiente isolado com CoSima;
- **OMNeT++** como simulador de rede;
- **Mosaik** como orquestrador de co-simulação (via CoSima).

O exemplo usado é o arquivo:
`01_simulators_and_connection_to_omnet.py`

---

## Pré-requisitos

### Recomendado
- Git
- Docker instalado e funcionando

### Se estiver no Windows com WSL/WSL2
- **Docker Desktop** instalado e **aberto** (o daemon precisa estar rodando)
- Para modo GUI: um X Server (ex.: **VcXsrv**) e utilitários X11 no WSL

---

## Quickstart (modo cmd)

1) Clone o repositório do CoSima:

```bash
git clone https://github.com/OFFIS-DAI/cosima
cd cosima
````

2. (Opcional) Crie e ative um ambiente virtual local (no host):

> Isso não é obrigatório para rodar via Docker, mas pode ser útil para tarefas auxiliares no host.

```bash
python -m venv venv
source venv/bin/activate
```

3. Construa a imagem Docker:

```bash
docker build -t cosima_i .
```

4. Inicie um container interativo:

```bash
docker run -it --name cosima_c cosima_i /bin/bash
```

---

## Executar o Tutorial 01

Já dentro do container, copie o Tutorial 01 para o diretório atual:

```bash
cp ~/models/cosima_core/scenarios/tutorial/01_simulators_and_connection_to_omnet.py .
```

Execute:

```bash
python3 01_simulators_and_connection_to_omnet.py
```

Se tudo estiver correto, o tutorial inicia a integração CoSima ↔ Mosaik ↔ OMNeT++ no modo `cmd`.

---

## Troubleshooting

### 1) Erro `NotFound` ao final da execução

Crie a pasta de resultados e instale utilitários necessários:

```bash
mkdir -p ../results
sudo apt-get update
sudo apt-get install -y psmisc
```

### 2) Docker no WSL não conecta

Verifique:

* **Docker Desktop aberto** e em execução
* Integração WSL habilitada no Docker Desktop (Settings → Resources/WSL Integration)

---

## Rodar com interface gráfica no WSL (modo gui)

> Esta seção é **apenas para Windows + WSL/WSL2**. Em Linux nativo, o fluxo pode ser diferente (normalmente o display já está disponível).

### Passo 1 — Instalar e configurar um X Server (Windows)

Instale o **VcXsrv**:
[https://sourceforge.net/projects/vcxsrv/](https://sourceforge.net/projects/vcxsrv/)

Configuração sugerida no VcXsrv:

1. **Multiple windows** e **Display number: 0**
2. Próxima tela: *Next* sem marcar nada
3. **Start no client**
4. Marque **Disable access control** e finalize

### Passo 2 — Preparar o WSL para X11

No WSL, descubra o gateway do Windows (IP usado no DISPLAY):

```bash
ip route | grep default
```

Exemplo de saída:

```text
default via 172.29.64.1 dev eth0
```

Configure o `DISPLAY` (substitua pelo IP mostrado no seu terminal):

```bash
export DISPLAY=172.29.64.1:0
echo $DISPLAY
```

Instale apps X11 para teste (se necessário):

```bash
sudo apt update
sudo apt install -y x11-apps
```

Teste:

```bash
xclock
```

Se abrir uma janela com relógio, o X11 está OK.

### Passo 3 — Subir o container com suporte a display

Rode o container repassando o DISPLAY e montando o socket X11:

```bash
docker run -it \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  cosima_i /bin/bash
```

### Passo 4 — Trocar o tutorial para modo GUI

Dentro do container, edite o arquivo do tutorial (após copiá-lo como mostrado antes) e altere:

De:

```python
START_MODE = 'cmd'
```

Para:

```python
START_MODE = 'gui'
```

Execute novamente:

```bash
python3 01_simulators_and_connection_to_omnet.py
```

Se estiver tudo configurado corretamente, o **OMNeT++ abrirá uma janela** permitindo visualizar o exemplo na interface gráfica.

---

## Notas de manutenção

* Se você for repetir o fluxo várias vezes, considere:

  * usar `docker start -ai cosima_c` para reentrar no mesmo container;
  * persistir scripts e resultados via `-v $(pwd):/work` para evitar cópias manuais.

---

## Licença e créditos

* CoSima: OFFIS / DAI (repositório original no GitHub)
* OMNeT++ e Mosaik: conforme licenças oficiais dos respectivos projetos

