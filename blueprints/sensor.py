"""Simulador do sensor (no ESP8266 esta rota devolve o valor real). Só com SIMULADOR_SENSOR=1."""
import random
import time

from flask import Blueprint, jsonify

from servicos.autenticacao import exigir_login

sensor = Blueprint('sensor', __name__)


@sensor.get('/read')
@exigir_login()
def read():
    time.sleep(1)  # finge que o sensor demora 1 segundo a estabilizar
    # random serve: são valores de teste, não segredos (por isso o nosec do bandit).
    # cond como o analogRead (inteiro 0-1023): leite normal ~300, mastite acima de 390.
    # Sem temp, como a placa atual (firmware/quickmast_esp8266)
    cond = random.randint(270, 420)               # nosec B311
    return jsonify({'cond': cond})
