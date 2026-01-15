# tscc-com-opentes

Repositório de código para armazenar as soluções desenvolvidas para simulação de comunicação.

Foi decidido que o simulador de comunicação será o **OMNeT++** e, para integrá-lo ao **Mosaik**, é utilizada a ferramenta **CoSima**. Abaixo está um passo a passo de como clonar o repositório do CoSima e executar o **tutorial 01** via Docker.

---

# Tutorial CoSima no Docker

Primeiro, é necessário clonar o repositório do CoSima disponível no GitHub:

```bash
git clone https://github.com/OFFIS-DAI/cosima
````

Para confirmar que o repositório foi clonado, execute:

```bash
ls
```

Deve aparecer a pasta `cosima`.

Em seguida, crie e ative um ambiente virtual antes de gerar a imagem Docker:

```bash
python -m venv venv
source venv/bin/activate
```

Com isso, seu ambiente virtual de nome `venv` estará criado e ativo.

Para criar a imagem Docker, entre na pasta `cosima` e execute:

```bash
cd cosima
docker build -t cosima_i .
```

> **Observação (WSL/WSL2):** se você estiver usando WSL/WSL2, certifique-se de que o **Docker Desktop** esteja aberto e em execução. Caso contrário, o Docker pode retornar erro de conexão.

Após finalizar o build, entre no container com:

```bash
docker run -it --name cosima_c cosima_i /bin/bash
```

Agora, copie o arquivo do tutorial **01** para o diretório atual (no container), para executá-lo “no centro do container”:

```bash
cp ~/models/cosima_core/scenarios/tutorial/01_simulators_and_connection_to_omnet.py .
```

Por fim, execute o tutorial:

```bash
python3 01_simulators_and_connection_to_omnet.py
```

Se aparecer um erro de `NotFound` ao final, execute:

```bash
mkdir -p ../results
sudo apt-get update
sudo apt-get install -y psmisc
```

Com isso você já terá o exemplo 01 do CoSima rodando em modo **cmd**. Para rodar com a interface gráfica do **OMNeT++**, siga os passos abaixo.

---

# Executar OMNeT++ com interface gráfica (WSL + X Server)

Primeiro, descubra o IP do Windows (gateway padrão):

```bash
ip route | grep default
```

O terminal retornará algo parecido com:

```text
default via 172.29.64.1 dev eth0
```

Agora configure o display:

```bash
export DISPLAY=172.29.64.1:0
echo $DISPLAY
```

Como neste cenário está sendo utilizado **WSL no Windows**, é necessário instalar um software que permita ao WSL abrir janelas gráficas. Uma opção é o **VcXsrv**:

[https://sourceforge.net/projects/vcxsrv/](https://sourceforge.net/projects/vcxsrv/)

Após instalar e abrir o VcXsrv, configure assim:

1. **Multiple windows**, **Display Number: 0** → *Next*
2. Segunda tela → *Next* (sem marcar nada)
3. **Start no client** → *Next*
4. **Disable access control** → *Finish*

Para um teste mínimo no terminal WSL, execute:

```bash
xclock
```

Se o comando não existir, instale:

```bash
sudo apt update
sudo apt install -y x11-apps
```

Agora rode o container com o display correto:

```bash
docker run -it \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  cosima_i /bin/bash
```

Dentro do container, será necessária apenas uma adaptação no código do tutorial 01. Procure a linha:

```python
START_MODE = 'cmd'
```

E altere para:

```python
START_MODE = 'gui'
```

Então execute novamente:

```bash
python3 01_simulators_and_connection_to_omnet.py
```

Agora, quando o código iniciar, uma janela do OMNeT++ deverá abrir, permitindo visualizar o exemplo funcionando na interface gráfica.

```

Se você quiser, eu também posso:
- transformar esse tutorial em **README mais “profissional”** (com pré-requisitos, troubleshooting e notas para Linux nativo vs WSL);
- ajustar para **Docker Compose** (melhor repetibilidade e menos comandos manuais).
```
