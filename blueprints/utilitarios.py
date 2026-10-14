"""Utilitários: estado do servidor e exportação em CSV."""
import csv
import io

from flask import Blueprint, Response, jsonify, request

from dao import banco
from servicos.autenticacao import exigir_login

utilitarios = Blueprint('utilitarios', __name__)


@utilitarios.get('/saude')
def saude():
    ok = banco.verificar_ligacao()
    return jsonify({'servidor': 'ok', 'banco': 'ok' if ok else 'indisponivel'}), (200 if ok else 503)


@utilitarios.get('/exportar.csv')
@exigir_login()
def exportar_csv():
    """Todas as leituras em CSV. Filtro opcional: /exportar.csv?brinco=BR-102"""
    brinco = request.args.get('brinco', '').strip() or None
    saida = io.StringIO()
    escritor = csv.writer(saida)
    escritor.writerow(['teste', 'vaca', 'data', 'teto', 'temp', 'cond', 'suspeito', 'motivo'])
    escritor.writerows(banco.linhas_csv(brinco))
    return Response(
        '﻿' + saida.getvalue(),   # BOM para o Excel abrir com acentos
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=quickmast.csv'}
    )
