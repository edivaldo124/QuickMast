"""Contador de tentativas falhadas numa janela de tempo (login, código MFA, troca de senha).

Fica em memória do processo: o gunicorn.conf.py usa 1 worker com threads para o contador
ser o mesmo para todos os pedidos. Com vários servidores, trocar por Flask-Limiter + Redis.
"""
import threading
import time


class Limitador:
    def __init__(self, janela_s=300, max_chaves=10_000):
        self.janela_s = janela_s
        self.max_chaves = max_chaves
        self._falhas = {}
        self._trava = threading.Lock()   # as threads do gunicorn partilham o dicionário

    def _recentes(self, chave, agora):
        recentes = [t for t in self._falhas.get(chave, ()) if agora - t < self.janela_s]
        if recentes:
            self._falhas[chave] = recentes
        else:
            self._falhas.pop(chave, None)   # contador expirado sai do dicionário
        return len(recentes)

    def quantas(self, chave):
        with self._trava:
            return self._recentes(chave, time.time())

    def excedido(self, chave, maximo):
        return self.quantas(chave) >= maximo

    def contar(self, *chaves):
        agora = time.time()
        with self._trava:
            if len(self._falhas) > self.max_chaves:   # muitas chaves diferentes: limpa as expiradas
                for chave in list(self._falhas):
                    self._recentes(chave, agora)
            for chave in chaves:
                self._falhas.setdefault(chave, []).append(agora)

    def limpar(self, chave):
        with self._trava:
            self._falhas.pop(chave, None)
