"""Páginas de entrada: login (senha e, com MFA, o código da app), registo e logout."""
import time
from urllib.parse import urlparse

from flask import (Blueprint, abort, current_app, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from dao import usuario_dao
from servicos import mfa as totp
from servicos.autenticacao import EMAIL_RE, usuario_atual
from servicos.limite import Limitador
from servicos.seguranca import auditar
from servicos.senhas import problema_senha

auth = Blueprint('auth', __name__)

# Hash falso: comparamos sempre uma senha, mesmo se o email não existir,
# para o tempo de resposta não revelar quais emails estão registados.
_HASH_FALSO = generate_password_hash('senha-falsa')

# Limites de falhas (servicos/limite.py), numa janela de 5 minutos:
# 5 por IP+email (adivinhar uma senha) e 20 por IP (testar muitos emails ou criar contas).
# Por conta, vindas de qualquer IP: à 20.ª falha sai um alerta (força bruta distribuída),
# sem bloquear o dono da conta. Código MFA: 10 falhas por hora por conta.
tentativas = Limitador(janela_s=300)
tentativas_mfa = Limitador(janela_s=3600)
_MAX_POR_CONTA = 5
_MAX_POR_IP = 20
_ALERTA_POR_CONTA = 20
MAX_FALHAS_MFA = 10
_MFA_VALIDADE_S = 300   # tempo para escrever o código depois de acertar a senha


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


def _bloqueado(ip, email=None):
    return (tentativas.excedido(ip, _MAX_POR_IP)
            or (email is not None and tentativas.excedido(f'{ip}|{email}', _MAX_POR_CONTA)))


def _login_falhou(ip, email):
    tentativas.contar(ip, f'{ip}|{email}', f'conta|{email}')
    auditar('login_falhou', email=email)
    if tentativas.quantas(f'conta|{email}') == _ALERTA_POR_CONTA:
        auditar('conta_sob_ataque', email=email)


def _iniciar_sessao(u):
    session.clear()            # evita reaproveitar uma sessão antiga
    session['uid'] = u['id']
    session['ver'] = u['sessao_versao']   # o logout e a troca de senha aumentam a versão no banco
    session.permanent = True


def _erro_login(destino, erro, status):
    return render_template('login.html', aba='entrar', next=destino, erro=erro), status


@auth.get('/login')
def login():
    if usuario_atual():
        return redirect('/ubere')
    return render_template('login.html', aba='entrar', erro=None,
                           next=request.args.get('next', '')[:500])


@auth.post('/login')
def login_post():
    # Cortados ao tamanho máximo: um email de 60 KB não fica na memória nem no log
    email = request.form.get('email', '')[:120].strip().lower()
    senha = request.form.get('senha', '')[:128]
    destino = request.form.get('next', '')[:500]
    ip = request.remote_addr

    if _bloqueado(ip, email):
        auditar('login_bloqueado', email=email)
        return _erro_login(destino, 'Muitas tentativas. Aguarde 5 minutos.', 429)

    u = usuario_dao.obter_por_email(email)
    senha_ok = check_password_hash(u['senha_hash'] if u else _HASH_FALSO, senha)
    if not (u and senha_ok and u['ativo']):
        _login_falhou(ip, email)
        return _erro_login(destino, 'Email ou senha inválidos.', 401)

    tentativas.limpar(f'{ip}|{email}')   # o contador do IP fica: entrar na própria conta não o zera
    if u['mfa_ativo']:
        # Senha certa, falta o código da app. Até lá a sessão não dá acesso a nada (não há 'uid').
        session.clear()
        session['mfa_uid'] = u['id']
        session['mfa_ate'] = time.time() + _MFA_VALIDADE_S
        session['mfa_next'] = _destino_seguro(destino)
        auditar('login_senha_ok', email=email)
        return redirect(url_for('auth.login_mfa'))

    _iniciar_sessao(u)
    auditar('login_ok')
    return redirect(_destino_seguro(destino))


def _mfa_pendente():
    """Quem acertou a senha e ainda não escreveu o código (None se não há ou se expirou)."""
    uid = session.get('mfa_uid')
    if not uid or time.time() > session.get('mfa_ate', 0):
        return None
    u = usuario_dao.obter_por_id(uid, interno=True)
    return u if u and u['ativo'] and u['mfa_ativo'] else None


def _erro_mfa(erro, status):
    return render_template('mfa.html', modo='entrar', erro=erro), status


@auth.get('/login/mfa')
def login_mfa():
    if _mfa_pendente() is None:
        return redirect(url_for('auth.login'))
    return render_template('mfa.html', modo='entrar', erro=None)


@auth.post('/login/mfa')
def login_mfa_post():
    u = _mfa_pendente()
    if u is None:
        session.clear()
        return redirect(url_for('auth.login'))
    ip, chave = request.remote_addr, f'mfa|{u["id"]}'
    if tentativas.excedido(ip, _MAX_POR_IP) or tentativas_mfa.excedido(chave, MAX_FALHAS_MFA):
        auditar('mfa_bloqueado', alvo=u['id'])
        return _erro_mfa('Muitas tentativas. Aguarde e tente mais tarde.', 429)

    passo = totp.verificar(u['totp_segredo'], request.form.get('codigo', '')[:20], u['totp_ultimo_passo'])
    if passo is None or not usuario_dao.usar_passo_totp(u['id'], passo):
        tentativas.contar(ip)
        tentativas_mfa.contar(chave)
        auditar('mfa_falhou', alvo=u['id'])   # senha certa + código errado: a senha pode ter vazado
        return _erro_mfa('Código inválido. Escreva o código que a app mostra agora.', 401)

    tentativas_mfa.limpar(chave)
    destino = session.get('mfa_next', '/ubere')
    _iniciar_sessao(u)
    auditar('login_ok', mfa=True)
    return redirect(destino)


@auth.post('/registrar')
def registrar():
    if not current_app.config['PERMITIR_REGISTO']:
        abort(403)
    if _bloqueado(request.remote_addr):
        return render_template('login.html', aba='criar', next='',
                               erro='Muitas tentativas. Aguarde 5 minutos.'), 429
    tentativas.contar(request.remote_addr)
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip().lower()
    senha = request.form.get('senha', '')

    if not 2 <= len(nome) <= 100:
        erro = 'Nome entre 2 e 100 caracteres.'
    elif len(email) > 120 or not EMAIL_RE.match(email):   # tamanho primeiro: a regex nunca vê texto enorme
        erro = 'Email inválido.'
    else:
        erro = problema_senha(senha, email)
        if erro is None and usuario_dao.obter_por_email(email):
            erro = 'Este email já está registado.'
    if erro:
        return render_template('login.html', aba='criar', erro=erro, next=''), 400

    u = usuario_dao.criar_usuario(nome, email, generate_password_hash(senha))
    _iniciar_sessao(u)
    auditar('registo', email=email)
    return redirect('/ubere')


@auth.post('/logout')
def logout():
    auditar('logout')
    u = usuario_atual()
    if u:
        usuario_dao.encerrar_sessoes(u['id'])   # cópias deste cookie deixam de servir
    session.clear()
    return redirect(url_for('auth.login'))
