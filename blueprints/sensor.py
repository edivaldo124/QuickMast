"""Leitura do sensor em /read, para a página do úbere (leitura ao vivo e captura de cada teto).

Em produção quem responde ao /read é o ESP8266: o Nginx repassa-lhe o pedido e este blueprint nem é
registado. No PC, sem Nginx, há três opções (ver servidor.py):
    PLACA_URL=http://<ip da placa>   o Flask repassa o /read para a placa (firmware/quickmast_esp8266)
    PLACA_URL=auto                   igual, mas procura a placa na rede local (a /24 do PC)
    SIMULADOR_SENSOR=1               valores de teste, sem placa
"""
import ipaddress
import json
import logging
import random
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.client import HTTPConnection, HTTPException
from urllib.parse import urlsplit

from flask import Blueprint, current_app, jsonify

from servicos.autenticacao import exigir_login

sensor = Blueprint('sensor', __name__)
log = logging.getLogger('quickmast.sensor')

ESPERA_PLACA = 5          # s: a placa mede em ~0,3 s (15 amostras); o resto é folga para o Wi-Fi
ESPERA_PROCURA = 1.5      # s por IP na procura: os IPs sem ninguém só desistem quando o tempo acaba
INTERVALO_PROCURA = 15    # s entre procuras: sem placa, a página continua a pedir /read a cada 2 s

_trava = threading.Lock()  # um pedido à placa de cada vez: ela só atende um cliente
_placa_achada = None       # IP onde a procura achou a placa (PLACA_URL=auto)
_ultima_procura = None


@sensor.get('/read')
@exigir_login()
def read():
    placa = current_app.config['PLACA_URL']
    if placa == 'auto':
        return _ler_placa_na_rede()
    if placa:
        endereco = urlsplit(placa)
        with _trava:
            leitura = _pedir_leitura(endereco.hostname, endereco.port or 80, ESPERA_PLACA)
        if leitura is None:
            return jsonify({'erro': f'A placa não respondeu em {placa}.'}), 504
        return jsonify(leitura)

    time.sleep(1)  # simulador: finge que o sensor demora 1 segundo a estabilizar
    # random serve: são valores de teste, não segredos (por isso o nosec do bandit).
    # cond como o analogRead (inteiro 0-1023): leite normal ~300, mastite acima de 390.
    # Sem temp, como a placa atual (firmware/quickmast_esp8266)
    cond = random.randint(270, 420)               # nosec B311
    return jsonify({'cond': cond})


def _pedir_leitura(host, porta, espera):
    """GET /read na placa. Devolve {'cond': int} (mais 'temp', se vier) ou None se não for a placa."""
    conexao = HTTPConnection(host, porta, timeout=espera)
    try:
        conexao.request('GET', '/read')
        resposta = conexao.getresponse()
        if resposta.status != 200:
            return None
        dados = json.loads(resposta.read(256))
    except (OSError, HTTPException, ValueError):   # sem resposta, ou uma que não é JSON
        return None
    finally:
        conexao.close()
    # Só passa adiante o que a página espera: outro aparelho da rede pode ter um /read qualquer
    if not isinstance(dados, dict):
        return None
    cond, temp = dados.get('cond'), dados.get('temp')
    if type(cond) is not int or not 0 <= cond <= 1023:
        return None
    leitura = {'cond': cond}
    if type(temp) in (int, float):
        leitura['temp'] = float(temp)
    return leitura


def _ler_placa_na_rede():
    """PLACA_URL=auto: lê do IP já achado; se a placa não responder, procura-a de novo na rede."""
    global _placa_achada, _ultima_procura
    with _trava:
        if _placa_achada:
            leitura = _pedir_leitura(_placa_achada, 80, ESPERA_PLACA)
            if leitura:
                return jsonify(leitura)
            log.info('placa_sem_resposta ip=%s', _placa_achada)
            _placa_achada, _ultima_procura = None, None   # pode ter mudado de IP: procura já
        if _ultima_procura is None or time.monotonic() - _ultima_procura >= INTERVALO_PROCURA:
            _ultima_procura = time.monotonic()
            _placa_achada, leitura = _procurar_placa()
            if _placa_achada:
                log.info('placa_encontrada ip=%s', _placa_achada)
                return jsonify(leitura)
    return jsonify({'erro': 'Não achei a placa na rede. Ela está ligada, no mesmo Wi-Fi do PC '
                            'e com o firmware quickmast_esp8266?'}), 504


def _procurar_placa():
    """Pede /read a todos os IPs da rede local (a /24 do PC). Devolve (ip, leitura) ou (None, None)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('10.255.255.255', 1))   # UDP: não envia nada, só escolhe a interface da rede
            meu_ip = s.getsockname()[0]
    except OSError:   # sem rede
        return None, None
    rede = ipaddress.ip_network(meu_ip + '/24', strict=False)
    ips = [str(ip) for ip in rede.hosts() if str(ip) != meu_ip]
    with ThreadPoolExecutor(max_workers=128) as pool:
        tarefas = {pool.submit(_pedir_leitura, ip, 80, ESPERA_PROCURA): ip for ip in ips}
        for tarefa in as_completed(tarefas):
            leitura = tarefa.result()
            if leitura:
                pool.shutdown(wait=False, cancel_futures=True)
                return tarefas[tarefa], leitura
    return None, None
