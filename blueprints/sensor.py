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
    # temp como o String(temperatura, 1) do ESP; cond como o analogRead (inteiro 0-1023)
    temp = round(random.uniform(38.0, 41.0), 1)   # nosec B311
    cond = random.randint(300, 550)               # nosec B311
    return jsonify({'temp': temp, 'cond': cond})
