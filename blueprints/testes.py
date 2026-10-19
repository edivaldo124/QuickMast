"""API dos testes de mastite: registar, consultar, vacas e estatísticas."""
from flask import Blueprint, jsonify, request

from dao import banco
from servicos.autenticacao import exigir_login, usuario_atual
from servicos.diagnostico import diagnosticar
from servicos.seguranca import auditar

testes_api = Blueprint('testes_api', __name__, url_prefix='/api')


def _validar(dados):
    """Valida o JSON recebido. Levanta ValueError com mensagem clara."""
    brinco = str(dados.get('brinco', '')).strip()
    if not brinco:
        raise ValueError('brinco da vaca em falta')
    if len(brinco) > 50:
        raise ValueError('brinco demasiado longo (máx. 50 caracteres)')

    bruto = dados.get('leituras')
    if not isinstance(bruto, list) or len(bruto) != 4:
        raise ValueError('envie exatamente 4 leituras')

    por_teto = {}
    for item in bruto:
        try:
            teto = int(item['teto'])
            cond = int(item['cond'])
            # temp é opcional: a placa atual só tem o sensor de condutividade (o DS18B20 saiu)
            temp = item.get('temp')
            temp = None if temp is None else float(temp)
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ValueError('cada leitura precisa de teto e cond numéricos (temp é opcional)')
        if teto not in (1, 2, 3, 4) or teto in por_teto:
            raise ValueError('tetos têm de ser 1, 2, 3 e 4, sem repetir')
        if temp is not None and not 0 < temp <= 60:
            raise ValueError(f'teto {teto}: temperatura inválida (sensor desligado?)')
        if not 0 <= cond <= 1023:
            raise ValueError(f'teto {teto}: condutividade fora de 0-1023')
        por_teto[teto] = {'temp': temp, 'cond': cond}

    observacao = (str(dados.get('observacao') or '').strip()[:200]) or None
    return brinco, [por_teto[t] for t in (1, 2, 3, 4)], observacao


@testes_api.post('/testes')
@exigir_login()
def criar_teste():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({'erro': 'corpo JSON inválido'}), 400
    try:
        brinco, leituras, observacao = _validar(dados)
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

    teste = banco.registrar_teste(brinco, leituras, diagnosticar(leituras), observacao,
                                    usuario_id=usuario_atual()['id'])
    return jsonify({'ok': True, 'teste': teste}), 201


@testes_api.get('/testes')
@exigir_login()
def listar_testes():
    brinco = request.args.get('brinco', '').strip() or None
    suspeitos = {'1': True, 'true': True, '0': False, 'false': False}.get(
        request.args.get('suspeitos', '').lower())
    limite = min(max(request.args.get('limite', 20, type=int), 1), 100)
    pagina = min(max(request.args.get('pagina', 1, type=int), 1), 100_000)   # OFFSET gigante dá erro 500 no Postgres

    itens, total = banco.listar_testes(brinco, suspeitos, limite, pagina)
    return jsonify({'total': total, 'pagina': pagina, 'limite': limite, 'testes': itens})


@testes_api.get('/testes/<int:teste_id>')
@exigir_login()
def obter_teste(teste_id):
    teste = banco.obter_teste(teste_id)
    if teste is None:
        return jsonify({'erro': 'teste não encontrado'}), 404
    return jsonify(teste)


@testes_api.delete('/testes/<int:teste_id>')
@exigir_login('admin')
def apagar_teste(teste_id):
    if not banco.apagar_teste(teste_id):
        return jsonify({'erro': 'teste não encontrado'}), 404
    auditar('teste_apagado', teste_id=teste_id)
    return jsonify({'ok': True})


@testes_api.get('/vacas')
@exigir_login()
def listar_vacas():
    limite = min(max(request.args.get('limite', 1000, type=int), 1), 1000)
    pagina = min(max(request.args.get('pagina', 1, type=int), 1), 100_000)
    return jsonify(banco.listar_vacas(limite, pagina))


@testes_api.get('/vacas/<brinco>/testes')
@exigir_login()
def testes_da_vaca(brinco):
    itens, total = banco.listar_testes(brinco=brinco, limite=100)
    if total == 0:
        return jsonify({'erro': 'vaca sem testes'}), 404
    return jsonify({'brinco': brinco, 'total': total, 'testes': itens})


@testes_api.get('/estatisticas')
@exigir_login()
def estatisticas():
    return jsonify(banco.estatisticas())

