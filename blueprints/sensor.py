"""Simulador do sensor (no ESP8266 esta rota devolve o valor real)."""
import random
import time

from flask import Blueprint, jsonify

from servicos.autenticacao import exigir_login

sensor = Blueprint('sensor', __name__)


@sensor.get('/read')
@exigir_login()
def read():
    time.sleep(1)  # finge que o sensor demora 1 segundo a estabilizar
    temp = round(random.uniform(38.0, 41.0), 1)   # igual ao String(temperatura, 1) do ESP
    cond = random.randint(300, 550)               # igual ao analogRead (inteiro 0-1023)
    return jsonify({'temp': temp, 'cond': cond})
