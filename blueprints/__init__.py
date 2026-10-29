"""Blueprints da aplicação, um por área:

    paginas      /, /ubere, /painel, /vacas/<brinco>, /usuarios   (HTML)
    auth         /login, /login/mfa, /registrar, /logout
    conta        /conta, /conta/senha, /conta/mfa
    testes_api   /api/testes, /api/vacas, /api/estatisticas
    usuarios_api /api/me, /api/usuarios
    sensor       /read no PC: repassado à placa (PLACA_URL) ou simulador (SIMULADOR_SENSOR=1)
    utilitarios  /saude, /exportar.csv
    erros        respostas de erro em JSON na API
"""
from blueprints.auth import auth
from blueprints.conta import conta
from blueprints.erros import erros
from blueprints.paginas import paginas
from blueprints.sensor import sensor
from blueprints.testes import testes_api
from blueprints.usuarios import usuarios_api
from blueprints.utilitarios import utilitarios


def registrar_blueprints(app):
    for bp in (paginas, auth, conta, testes_api, usuarios_api, utilitarios, erros):
        app.register_blueprint(bp)
    # Em produção quem responde ao /read é o ESP8266 (o Nginx repassa) e este blueprint fica de fora
    if app.config['PLACA_URL'] or app.config['SIMULADOR_SENSOR']:
        app.register_blueprint(sensor)
