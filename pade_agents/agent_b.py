import json
from pade.core.agent import Agent
from twisted.internet.task import LoopingCall

class AgenteB(Agent):
    def __init__(self, aid):
        super().__init__(aid=aid, debug=False)
        self.val_in = "" 

    def on_start(self):
        super().on_start()
        print(f"[{self.aid.localname}] Iniciando monitoramento da rede...")
        
        # O LoopingCall roda a função verificar_mensagem a cada 1.0 segundo
        # Isso atua em perfeita harmonia com o 'step' do Mosaik.
        self.monitor = LoopingCall(self.verificar_mensagem)
        self.monitor.start(1.0)

    def verificar_mensagem(self):
        if self.val_in != "":
            try:
                mensagem = json.loads(self.val_in)
                print(f"[{self.aid.localname}] MENSAGEM RECEBIDA COM SUCESSO!")
                print(f"  -> Origem: {mensagem.get('origem')}")
                print(f"  -> Payload: {mensagem.get('payload')}")
                
            except json.JSONDecodeError:
                print(f"[{self.aid.localname}] Erro: Dado inválido recebido: {self.msg_in}")
                
            # Limpa o buffer após processar
            self.val_in = ""