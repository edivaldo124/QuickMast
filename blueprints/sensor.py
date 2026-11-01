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
from urllib.parse import urlencode, urlsplit

from flask import Blueprint, current_app, jsonify

from servicos.autenticacao import exigir_login, usuario_atual

sensor = Blueprint('sensor', __name__)
log = logging.getLogger('quickmast.sensor')

ESPERA_PLACA = 5          # s: a placa mede em ~0,3 s (15 amostras); o resto é folga para o Wi-Fi
ESPERA_FILA = 1.5         # s: /fila na placa não lê o sensor, responde logo se ela estiver ligada
ESPERA_PROCURA = 1.5      # s por IP na procura: os IPs sem ninguém só desistem quando o tempo acaba
INTERVALO_PROCURA = 15    # s entre procuras: sem placa, a página continua a pedir /read a cada 2 s

_trava = threading.Lock()  # um pedido à placa de cada vez: ela só atende um cliente
_placa_achada = None       # IP onde a procura achou a placa (PLACA_URL=auto)
_ultima_procura = None
_ultima_falha_fila = None


@sensor.get('/read')
@exigir_login()
def read():
    placa = current_app.config['PLACA_URL']
    if placa == 'auto':
        return _ler_placa_na_rede()
    if placa:
        endereco = urlsplit(placa)
        host, porta = endereco.hostname, endereco.port or 80
        with _trava:
            leitura = _pedir_leitura(host, porta, ESPERA_PLACA)
            if leitura and leitura.get('pendentes', 0) > 0:
                _sincronizar_fila(host, porta, usuario_atual()['id'])
        if leitura is None:
            return jsonify({'erro': f'A placa não respondeu em {placa}.'}), 504
        return jsonify(leitura)

    time.sleep(1)  # simulador: finge que o sensor demora 1 segundo a estabilizar
    # random serve: são valores de teste, não segredos (por isso o nosec do bandit).
    # cond como o analogRead (inteiro 0-1023): leite normal ~300 (cada vaca tem o seu nível).
    # Sem temp, como a placa atual (firmware/quickmast_esp8266)
    cond = random.randint(270, 420)               # nosec B311
    return jsonify({'cond': cond})


def _pedir_leitura(host, porta, espera):
    """GET /read na placa. Devolve {'cond': int} (mais 'temp' e 'pendentes', se vierem) ou None."""
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
    cond, temp, pendentes = dados.get('cond'), dados.get('temp'), dados.get('pendentes')
    if type(cond) is not int or not 0 <= cond <= 1023:
        return None
    leitura = {'cond': cond}
    if type(temp) in (int, float):
        leitura['temp'] = float(temp)
    if type(pendentes) is int and pendentes >= 0:
        leitura['pendentes'] = pendentes
    return leitura


def _pedir_fila(host, porta):
    """GET /fila na placa: lê o teste mais antigo salvo no curral, sem o apagar da placa."""
    conexao = HTTPConnection(host, porta, timeout=ESPERA_FILA)
    try:
        conexao.request('GET', '/fila')
        resposta = conexao.getresponse()
        if resposta.status != 200:
            return None
        dados = json.loads(resposta.read(1024))
    except (OSError, HTTPException, ValueError):
        return None
    finally:
        conexao.close()
    return dados if isinstance(dados, dict) else None


def _confirmar_fila(host, porta, seq, teste_id, tetos_afetados):
    """POST /fila/confirmar: só depois de o teste estar gravado no PostgreSQL é que a placa o apaga."""
    corpo = urlencode({
        'seq': seq,
        'id': teste_id,
        'tetos_afetados': ','.join(str(t) for t in tetos_afetados),
    })
    conexao = HTTPConnection(host, porta, timeout=ESPERA_FILA)
    try:
        conexao.request('POST', '/fila/confirmar', body=corpo,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
        resposta = conexao.getresponse()
        if resposta.status != 200:
            return False
        dados = json.loads(resposta.read(256))
    except (OSError, HTTPException, ValueError):
        return False
    finally:
        conexao.close()
    return isinstance(dados, dict) and dados.get('ok') is True


def _sincronizar_fila(host, porta, usuario_id):
    """Grava no servidor todos os testes salvos na placa e confirma cada um para ela os apagar."""
    from blueprints.testes import gravar_teste_validado

    sincronizados = 0
    for _ in range(50):
        item = _pedir_fila(host, porta)
        if item is None:
            return None
        if not item.get('pendentes'):
            break
        seq = item.get('seq')
        if type(seq) is not int or seq <= 0:
            break
        try:
            teste, _ = gravar_teste_validado(item, usuario_id, origem=f'placa:{host}')
        except ValueError as e:
            log.warning('placa_fila_invalida host=%s seq=%s erro=%s', host, seq, e)
            break
        if not teste or type(teste.get('id')) is not int or teste['id'] <= 0:
            break
        if not _confirmar_fila(host, porta, seq, teste['id'], teste.get('tetos_afetados', [])):
            break
        sincronizados += 1
        log.info('placa_teste_sincronizado host=%s seq=%s teste_id=%s vaca=%s',
                 host, seq, teste['id'], teste.get('vaca'))
    return sincronizados


def sincronizar_se_houver_placa(usuario_id):
    """Chamado ao listar testes: se a placa estiver ligada (PLACA_URL), recolhe a fila salva nela."""
    global _ultima_falha_fila
    placa = current_app.config.get('PLACA_URL', '')
    if not placa:
        return 0
    if placa == 'auto':
        if not _placa_achada:
            return 0
        host, porta = _placa_achada, 80
    else:
        endereco = urlsplit(placa)
        host, porta = endereco.hostname, endereco.port or 80
    if _ultima_falha_fila is not None and time.monotonic() - _ultima_falha_fila < INTERVALO_PROCURA:
        return 0
    if not _trava.acquire(blocking=False):
        return 0
    try:
        res = _sincronizar_fila(host, porta, usuario_id)
        if res is None:
            _ultima_falha_fila = time.monotonic()
            return 0
        _ultima_falha_fila = None
        return res
    finally:
        _trava.release()


def _ler_placa_na_rede():
    """PLACA_URL=auto: lê do IP já achado; se a placa não responder, procura-a de novo na rede."""
    global _placa_achada, _ultima_procura
    uid = usuario_atual()['id']
    with _trava:
        if _placa_achada:
            leitura = _pedir_leitura(_placa_achada, 80, ESPERA_PLACA)
            if leitura:
                if leitura.get('pendentes', 0) > 0:
                    _sincronizar_fila(_placa_achada, 80, uid)
                return jsonify(leitura)
            log.info('placa_sem_resposta ip=%s', _placa_achada)
            _placa_achada, _ultima_procura = None, None   # pode ter mudado de IP: procura já
        if _ultima_procura is None or time.monotonic() - _ultima_procura >= INTERVALO_PROCURA:
            _ultima_procura = time.monotonic()
            _placa_achada, leitura = _procurar_placa()
            if _placa_achada:
                log.info('placa_encontrada ip=%s', _placa_achada)
                if leitura.get('pendentes', 0) > 0:
                    _sincronizar_fila(_placa_achada, 80, uid)
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
