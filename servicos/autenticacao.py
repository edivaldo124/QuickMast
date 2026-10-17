"""Utilizador da sessão e proteção de rotas (usado por todos os blueprints)."""
import logging
import os
import re
from functools import wraps

from flask import abort, g, jsonify, redirect, request, session, url_for

from dao import usuario_dao
from servicos.seguranca import auditar

# Sem ambiguidade (cada parte entre pontos não tem ponto): tempo linear, sem ReDoS.
# Mesmo assim, validar o tamanho ANTES de aplicar a regex.
EMAIL_RE = re.compile(r'^[^@\s.]+(?:\.[^@\s.]+)*@[^@\s.]+(?:\.[^@\s.]+)+$')

# Rotas abertas sem sessão. Tudo o resto exige login, mesmo se faltar o @exigir_login numa rota nova.
_PUBLICAS = {'static', 'paginas.index', 'auth.login', 'auth.login_post', 'auth.login_mfa',
             'auth.login_mfa_post', 'auth.registrar', 'auth.logout', 'utilitarios.saude'}

# O admin sem verificação em dois passos só pode configurá-la (ou sair)
_SEM_MFA = {'conta.mfa', 'conta.mfa_post'}


def usuario_atual():
    """Lê o utilizador da sessão (1 consulta por pedido).
    Sem sessão se estiver inativo ou se o cookie for de uma versão antiga (logout, troca de senha)."""
    if 'usuario' not in g:
        uid = session.get('uid')
        u = usuario_dao.obter_por_id(uid, interno=True) if uid else None
        valido = u and u['ativo'] and session.get('ver') == u['sessao_versao']
        g.usuario = usuario_dao.publico(u) if valido else None
    return g.usuario


def _sem_sessao():
    if request.path.startswith('/api/'):
        return jsonify({'erro': 'autenticação necessária'}), 401
    return redirect(url_for('auth.login', next=request.path))


def negar_por_omissao(app):
    """Exige sessão em todas as rotas que não estão em _PUBLICAS (os perfis continuam no decorador)."""
    @app.before_request
    def exigir_sessao():
        if request.endpoint is None or request.endpoint in _PUBLICAS:
            return None   # 404/405 seguem o tratamento normal
        u = usuario_atual()
        if u is None:
            return _sem_sessao()
        if u['perfil'] == 'admin' and not u['mfa_ativo'] and request.endpoint not in _SEM_MFA:
            if request.path.startswith('/api/'):
                return jsonify({'erro': 'ative a verificação em dois passos em /conta/mfa'}), 403
            return redirect(url_for('conta.mfa'))


def exigir_login(*perfis):
    """Protege uma rota. Sem perfis = qualquer utilizador autenticado.
    O admin passa sempre. Na API responde 401/403 em JSON; nas páginas redireciona."""
    def decorador(f):
        @wraps(f)
        def interno(*args, **kwargs):
            u = usuario_atual()
            if u is None:
                return _sem_sessao()
            if perfis and u['perfil'] != 'admin' and u['perfil'] not in perfis:
                auditar('acesso_negado', rota=request.path, perfil=u['perfil'])
                if request.path.startswith('/api/'):
                    return jsonify({'erro': 'sem permissão'}), 403
                abort(403)
            return f(*args, **kwargs)
        return interno
    return decorador


def _hash_valido(senha_hash):
    """Formato do werkzeug: metodo$sal$hash (ex.: scrypt:32768:8:1$...$...)."""
    partes = senha_hash.split('$')
    return len(partes) == 3 and all(partes) and partes[0].split(':')[0] in ('scrypt', 'pbkdf2')


def garantir_admin():
    """Cria o admin inicial com ADMIN_EMAIL / ADMIN_SENHA_HASH (.env), se o email ainda não existir.
    O .env só tem o hash da senha (gerado por definir_senha_admin.py), nunca a senha em texto.
    Mudar ADMIN_SENHA_HASH depois não altera uma conta já criada."""
    log = logging.getLogger(__name__)
    if os.environ.get('ADMIN_SENHA'):
        log.warning('ADMIN_SENHA (senha em texto) é ignorada: use ADMIN_SENHA_HASH (python3 definir_senha_admin.py).')
    email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
    senha_hash = os.environ.get('ADMIN_SENHA_HASH', '').strip()
    if not email or not senha_hash:
        if usuario_dao.contar_admins_ativos() == 0:
            log.warning('Não há nenhum admin ativo: defina ADMIN_SENHA_HASH (python3 definir_senha_admin.py).')
        return
    if usuario_dao.obter_por_email(email):
        return
    if not EMAIL_RE.match(email) or not _hash_valido(senha_hash):
        log.warning('Admin inicial não criado: ADMIN_EMAIL ou ADMIN_SENHA_HASH inválido.')
        return
    nome = os.environ.get('ADMIN_NOME', '').strip() or 'Administrador'
    usuario_dao.criar_usuario(nome, email, senha_hash, perfil='admin')
    log.info('Admin inicial criado: %s', email)
