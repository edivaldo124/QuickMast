"""Páginas de entrada: login, registo e logout."""
import time
from urllib.parse import urlparse

from flask import (Blueprint, abort, current_app, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from dao import usuario_dao
from servicos.autenticacao import EMAIL_RE, usuario_atual

auth = Blueprint('auth', __name__)

# Hash falso: comparamos sempre uma senha, mesmo se o email não existir,
# para o tempo de resposta não revelar quais emails estão registados.
_HASH_FALSO = generate_password_hash('senha-falsa')

# Limite de tentativas falhadas (em memória): 5 por 5 minutos, por IP+email
_falhas = {}
_MAX_FALHAS = 5
_JANELA_S = 300


@auth.app_context_processor
def injetar_usuario():
    """Disponibiliza {{ usuario }} em todos os templates."""
    return {'usuario': usuario_atual()}


def _destino_seguro(destino):
    """Evita 'open redirect': só aceita caminhos internos (ex.: /ubere)."""
    if not destino or not destino.startswith('/') or destino.startswith('//') or '\\' in destino:
        return '/ubere'
    p = urlparse(destino)
    return '/ubere' if p.scheme or p.netloc else destino


def _bloqueado(chave):
    agora = time.time()
    recentes = [t for t in _falhas.get(chave, []) if agora - t < _JANELA_S]
    _falhas[chave] = recentes
    return len(recentes) >= _MAX_FALHAS


def _iniciar_sessao(u):
    session.clear()            # evita reaproveitar uma sessão antiga
    session['uid'] = u['id']
    session.permanent = True


@auth.get('/login')
def login():
    if usuario_atual():
        return redirect('/ubere')
    return render_template('login.html', aba='entrar', erro=None,
                           next=request.args.get('next', ''))


@auth.post('/login')
def login_post():
    email = request.form.get('email', '').strip().lower()
    senha = request.form.get('senha', '')
    destino = request.form.get('next', '')
    chave = f'{request.remote_addr}|{email}'

    if _bloqueado(chave):
        return render_template('login.html', aba='entrar', next=destino,
                               erro='Muitas tentativas. Aguarde 5 minutos.'), 429

    u = usuario_dao.obter_por_email(email)
    senha_ok = check_password_hash(u['senha_hash'] if u else _HASH_FALSO, senha)
    if not (u and senha_ok and u['ativo']):
        _falhas.setdefault(chave, []).append(time.time())
        return render_template('login.html', aba='entrar', next=destino,
                               erro='Email ou senha inválidos.'), 401

    _falhas.pop(chave, None)
    _iniciar_sessao(u)
    return redirect(_destino_seguro(destino))


@auth.post('/registrar')
def registrar():
    if not current_app.config['PERMITIR_REGISTO']:
        abort(403)
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip().lower()
    senha = request.form.get('senha', '')

    erro = None
    if not 2 <= len(nome) <= 100:
        erro = 'Nome entre 2 e 100 caracteres.'
    elif not EMAIL_RE.match(email) or len(email) > 120:
        erro = 'Email inválido.'
    elif not 8 <= len(senha) <= 128:
        erro = 'A senha precisa de 8 a 128 caracteres.'
    elif usuario_dao.obter_por_email(email):
        erro = 'Este email já está registado.'
    if erro:
        return render_template('login.html', aba='criar', erro=erro, next=''), 400

    u = usuario_dao.criar_usuario(nome, email, generate_password_hash(senha))
    _iniciar_sessao(u)
    return redirect('/ubere')


@auth.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
