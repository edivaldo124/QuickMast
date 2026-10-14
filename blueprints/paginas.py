"""Páginas HTML. Os dados de cada página vêm da API (fetch no JavaScript)."""
from flask import Blueprint, render_template

from servicos.autenticacao import exigir_login

paginas = Blueprint('paginas', __name__)


@paginas.get('/')
def index():
    return render_template('index.html')


@paginas.get('/ubere')
@exigir_login()
def ubere():
    return render_template('ubere.html')


@paginas.get('/painel')
@exigir_login()
def painel():
    return render_template('painel.html')     # dados: GET /api/estatisticas


@paginas.get('/vacas/<brinco>')
@exigir_login()
def historico_vaca(brinco):
    return render_template('vaca.html', brinco=brinco)   # dados: GET /api/vacas/<brinco>/testes


@paginas.get('/usuarios')
@exigir_login('admin')
def usuarios():
    return render_template('usuarios.html')   # dados: GET /api/usuarios
