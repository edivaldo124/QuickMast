"""Blueprints da aplicação, um por área:

    paginas      /, /ubere, /painel, /vacas/<brinco>, /usuarios   (HTML)
    auth         /login, /registrar, /logout
    testes_api   /api/testes, /api/vacas, /api/estatisticas
    usuarios_api /api/me, /api/usuarios
    sensor       /read (simulador do ESP8266)
    utilitarios  /saude, /exportar.csv
    erros        respostas de erro em JSON na API
"""
from blueprints.auth import auth
from blueprints.erros import erros
from blueprints.paginas import paginas
from blueprints.sensor import sensor
from blueprints.testes import testes_api
from blueprints.usuarios import usuarios_api
from blueprints.utilitarios import utilitarios


def registrar_blueprints(app):
    for bp in (paginas, auth, testes_api, usuarios_api, sensor, utilitarios, erros):
        app.register_blueprint(bp)
