"""API de utilizadores: o próprio (/api/me) e a gestão pelo admin."""
from flask import Blueprint, jsonify, request

from dao import usuario_dao
from modelos.usuario import PERFIS
from servicos.autenticacao import exigir_login, usuario_atual
from servicos.seguranca import auditar

usuarios_api = Blueprint('usuarios_api', __name__, url_prefix='/api')


@usuarios_api.get('/me')
@exigir_login()
def eu():
    return jsonify(usuario_atual())


@usuarios_api.get('/usuarios')
@exigir_login('admin')
def listar():
    return jsonify(usuario_dao.listar_usuarios())


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
