"""Utilitários: estado do servidor e exportação em CSV."""
import csv
import io

from flask import Blueprint, Response, jsonify, request, stream_with_context

from dao import banco
from servicos.autenticacao import exigir_login
from servicos.seguranca import auditar

utilitarios = Blueprint('utilitarios', __name__)


def _celula_segura(valor):
    """Texto começado por = + - @ vira fórmula no Excel: o apóstrofo força-o a ser só texto."""
    if isinstance(valor, str) and valor[:1] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + valor
    return valor


@utilitarios.get('/saude')
def saude():
    ok = banco.verificar_ligacao()
    return jsonify({'servidor': 'ok', 'banco': 'ok' if ok else 'indisponivel'}), (200 if ok else 503)


@utilitarios.get('/exportar.csv')
@exigir_login()
def exportar_csv():
    """Todas as leituras em CSV. Filtro opcional: /exportar.csv?brinco=BR-102
    Enviado aos bocados à medida que sai do banco: a memória não cresce com o número de testes."""
    brinco = request.args.get('brinco', '').strip()[:50] or None
    auditar('exportar_csv', brinco=brinco)

    def gerar():
        saida = io.StringIO()
        escritor = csv.writer(saida)
        saida.write('\ufeff')   # BOM para o Excel abrir com acentos
        escritor.writerow(['teste', 'vaca', 'data', 'teto', 'temp', 'cond', 'suspeito', 'motivo'])
        for linha in banco.linhas_csv(brinco):
            escritor.writerow([_celula_segura(c) for c in linha])
            if saida.tell() > 16_384:
                yield saida.getvalue()
                saida.seek(0)
                saida.truncate()
        yield saida.getvalue()

    return Response(
        stream_with_context(gerar()),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=quickmast.csv'}
    )
