"""Utilizador da sessão e proteção de rotas (usado por todos os blueprints)."""
import logging
import os
import re
from functools import wraps

from flask import abort, g, jsonify, redirect, request, session, url_for
from werkzeug.security import generate_password_hash

from dao import usuario_dao

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def usuario_atual():
    """Lê o utilizador da sessão (1 consulta por pedido). Inativo = sem sessão."""
    if 'usuario' not in g:
        uid = session.get('uid')
        u = usuario_dao.obter_por_id(uid) if uid else None
        g.usuario = u if u and u['ativo'] else None
    return g.usuario


def exigir_login(*perfis):
    """Protege uma rota. Sem perfis = qualquer utilizador autenticado.
    O admin passa sempre. Na API responde 401/403 em JSON; nas páginas redireciona."""
    def decorador(f):
        @wraps(f)
        def interno(*args, **kwargs):
            u = usuario_atual()
            if u is None:
                if request.path.startswith('/api/'):
                    return jsonify({'erro': 'autenticação necessária'}), 401
                return redirect(url_for('auth.login', next=request.path))
            if perfis and u['perfil'] != 'admin' and u['perfil'] not in perfis:
                if request.path.startswith('/api/'):
                    return jsonify({'erro': 'sem permissão'}), 403
                abort(403)
            return f(*args, **kwargs)
        return interno
    return decorador


def garantir_admin():
    """Cria o admin inicial com ADMIN_EMAIL / ADMIN_SENHA (.env), se o email ainda não existir.
    A senha só é guardada como hash; mudar ADMIN_SENHA depois não altera uma conta já criada."""
    log = logging.getLogger(__name__)
    email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
    senha = os.environ.get('ADMIN_SENHA', '')
    if not email or not senha:
        return
    if usuario_dao.obter_por_email(email):
        return
    if not EMAIL_RE.match(email) or not 8 <= len(senha) <= 128:
        log.warning('Admin inicial não criado: ADMIN_EMAIL inválido ou ADMIN_SENHA fora de 8-128 caracteres.')
        return
    nome = os.environ.get('ADMIN_NOME', '').strip() or 'Administrador'
    usuario_dao.criar_usuario(nome, email, generate_password_hash(senha), perfil='admin')
    log.info('Admin inicial criado: %s', email)
