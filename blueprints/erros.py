"""Erros: na API respondem em JSON; nas páginas seguem o tratamento normal do Flask."""
from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import HTTPException

erros = Blueprint('erros', __name__)


@erros.app_errorhandler(HTTPException)
def erro_http(e):
    if request.path.startswith('/api/'):
        return jsonify({'erro': e.description}), e.code
    return e


@erros.app_errorhandler(Exception)
def erro_geral(e):
    current_app.logger.exception('Erro inesperado')
    if request.path.startswith('/api/'):
        return jsonify({'erro': 'erro interno do servidor'}), 500
    raise e
