"""API dos testes de mastite: registar, consultar, vacas e estatísticas."""
import re

from flask import Blueprint, jsonify, request

from dao import banco
from servicos.autenticacao import exigir_login, usuario_atual
from servicos.diagnostico import BASE_MINIMO, BASE_TESTES, diagnosticar
from servicos.seguranca import auditar

testes_api = Blueprint('testes_api', __name__, url_prefix='/api')


def _normalizar_brinco(brinco):
    """Uma forma só para cada brinco: 'br 102', 'Br_102' e 'BR-102' são a mesma vaca (BR-102).
    A página /ubere faz o mesmo (normalizarBrinco em ubere.js) para mostrar o brinco como fica gravado."""
    return re.sub(r'[\s_-]+', '-', brinco).strip('-').upper()


def _validar(dados):
    """Valida o JSON recebido. Levanta ValueError com mensagem clara."""
    brinco = _normalizar_brinco(str(dados.get('brinco', '')))
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


# Evita duplicar um teste da placa se o Wi-Fi cair depois de gravar no banco mas antes de a
# confirmação chegar ao ESP8266 (a placa mantém o teste salvo até receber a certeza e reenvia-o).
_ultimos_da_placa = {}


def gravar_teste_validado(dados, usuario_id, origem='api'):
    brinco, leituras, observacao = _validar(dados)
    seq = dados.get('seq')
    chave = None
    if type(seq) is int and seq > 0:
        conds = tuple(l['cond'] for l in leituras)
        chave = (origem, usuario_id, seq, brinco, conds)
        if chave in _ultimos_da_placa:
            existente, hist = _ultimos_da_placa[chave]
            if banco.obter_teste(existente['id']) is not None:
                return existente, hist

    # Cada vaca tem o seu nível de condutividade: o diagnóstico compara com o histórico dela
    diagnostico = diagnosticar(leituras, banco.historico_da_vaca(brinco, BASE_TESTES))
    teste = banco.registrar_teste(brinco, leituras, diagnostico, observacao,
                                  usuario_id=usuario_id)
    historico = {'base': [d['base'] for d in diagnostico], 'minimo': BASE_MINIMO}
    if chave is not None:
        if len(_ultimos_da_placa) >= 128:
            _ultimos_da_placa.pop(next(iter(_ultimos_da_placa)))
        _ultimos_da_placa[chave] = (teste, historico)
    return teste, historico


@testes_api.post('/testes')
@exigir_login()
def criar_teste():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({'erro': 'corpo JSON inválido'}), 400
    try:
        teste, historico = gravar_teste_validado(dados, usuario_atual()['id'])
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

    # base: linha de base de cada teto (None = ainda sem histórico, só comparado com os outros tetos)
    return jsonify({'ok': True, 'teste': teste, 'historico': historico}), 201


@testes_api.get('/testes')
@exigir_login()
def listar_testes():
    from blueprints.sensor import sincronizar_se_houver_placa
    sincronizar_se_houver_placa(usuario_atual()['id'])

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

