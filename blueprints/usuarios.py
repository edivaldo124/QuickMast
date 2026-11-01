"""API de utilizadores: o próprio (/api/me) e a gestão pelo admin."""
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from dao import usuario_dao
from modelos.usuario import PERFIS
from servicos.autenticacao import EMAIL_RE, exigir_login, usuario_atual
from servicos.seguranca import auditar
from servicos.senhas import problema_senha

usuarios_api = Blueprint('usuarios_api', __name__, url_prefix='/api')


@usuarios_api.get('/me')
@exigir_login()
def eu():
    return jsonify(usuario_atual())


@usuarios_api.get('/usuarios')
@exigir_login('admin')
def listar():
    return jsonify(usuario_dao.listar_usuarios())


@usuarios_api.post('/usuarios')
@exigir_login('admin')
def criar():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({'erro': 'corpo JSON inválido'}), 400
    nome = str(dados.get('nome') or '').strip()
    email = str(dados.get('email') or '').strip().lower()
    senha = str(dados.get('senha') or '')
    perfil = str(dados.get('perfil') or 'operador').strip()

    if not 2 <= len(nome) <= 100:
        return jsonify({'erro': 'Nome entre 2 e 100 caracteres.', 'campo': 'nome'}), 400
    if len(email) > 120 or not EMAIL_RE.match(email):
        return jsonify({'erro': 'Email inválido.', 'campo': 'email'}), 400
    if perfil not in ('operador', 'veterinario'):
        return jsonify({'erro': 'Perfil inválido.', 'campo': 'perfil'}), 400
    erro_senha = problema_senha(senha, email)
    if erro_senha:
        return jsonify({'erro': erro_senha, 'campo': 'senha'}), 400
    if usuario_dao.obter_por_email(email):
        return jsonify({'erro': 'Este email já está registado.', 'campo': 'email'}), 400

    novo = usuario_dao.criar_usuario(nome, email, generate_password_hash(senha), perfil=perfil)
    auditar('usuario_criado', alvo=novo['id'], email=email, perfil=perfil)
    return jsonify(usuario_dao.publico(novo)), 201


@usuarios_api.patch('/usuarios/<int:usuario_id>')
@exigir_login('admin')
def atualizar(usuario_id):
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({'erro': 'corpo JSON inválido'}), 400
    perfil = dados.get('perfil')
    ativo = dados.get('ativo')

    if perfil is not None and perfil not in PERFIS:
        return jsonify({'erro': 'perfil inválido'}), 400
    if ativo is not None and not isinstance(ativo, bool):
        return jsonify({'erro': 'ativo tem de ser true ou false'}), 400
    if perfil is None and ativo is None:
        return jsonify({'erro': 'nada para alterar'}), 400

    alvo = usuario_dao.obter_por_id(usuario_id)
    if alvo is None:
        return jsonify({'erro': 'utilizador não encontrado'}), 404

    # Regras de segurança: ninguém tira o próprio acesso nem o do último admin
    if usuario_id == usuario_atual()['id']:
        return jsonify({'erro': 'não pode alterar a sua própria conta'}), 400
    perde_admin = alvo['perfil'] == 'admin' and (perfil not in (None, 'admin') or ativo is False)
    if perde_admin and usuario_dao.contar_admins_ativos() <= 1:
        return jsonify({'erro': 'tem de existir pelo menos um admin ativo'}), 400

    auditar('usuario_alterado', alvo=usuario_id, perfil=perfil, ativo=ativo)
    return jsonify(usuario_dao.atualizar_usuario(usuario_id, perfil, ativo))
