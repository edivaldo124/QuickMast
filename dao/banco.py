import logging
import os

from sqlalchemy import create_engine, inspect, make_url, select, func, case
from sqlalchemy.orm import Session, selectinload, contains_eager

from modelos import Base, Vaca, Teste, Leitura

log = logging.getLogger(__name__)

# Endereço do PostgreSQL, vindo da variável de ambiente DATABASE_URL (.env).
# Formato: postgresql+psycopg2://utilizador:senha@servidor:porta/base
# A aplicação usa um utilizador que só lê e escreve dados; o dono do banco (DATABASE_URL_ADMIN)
# só entra em criar_tabela(), chamado por "flask --app servidor iniciar".
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL não definida: copie .env.example para .env e preencha.')

# pool_pre_ping testa a ligação antes de a usar (evita erros se o banco reiniciar)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Colunas acrescentadas depois da 1.ª versão: o create_all não altera tabelas que já existem.
# Só constantes daqui entram no ALTER TABLE.
_COLUNAS_NOVAS = {
    'usuarios': [
        ('sessao_versao', 'INTEGER NOT NULL DEFAULT 0'),
        ('totp_segredo', 'VARCHAR(32)'),
        ('totp_ultimo_passo', 'INTEGER'),
    ],
}

# Colunas que passaram a aceitar NULL (o create_all também não muda isto). Só constantes daqui.
_COLUNAS_OPCIONAIS = {
    'leituras': ['temp'],   # o sensor de temperatura saiu da placa
}


def _migrar(eng):
    insp = inspect(eng)
    with eng.begin() as con:
        for tabela, colunas in _COLUNAS_NOVAS.items():
            existentes = {c['name'] for c in insp.get_columns(tabela)}
            for nome, tipo in colunas:
                if nome not in existentes:
                    con.exec_driver_sql(f'ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}')
                    log.info('Coluna %s.%s criada', tabela, nome)
        for tabela, colunas in _COLUNAS_OPCIONAIS.items():
            obrigatorias = {c['name'] for c in insp.get_columns(tabela) if not c['nullable']}
            for nome in colunas:
                if nome not in obrigatorias:
                    continue
                if eng.dialect.name != 'postgresql':
                    log.warning('%s.%s continua NOT NULL: só o PostgreSQL é migrado (apague o banco local)',
                                tabela, nome)
                    continue
                con.exec_driver_sql(f'ALTER TABLE {tabela} ALTER COLUMN {nome} DROP NOT NULL')
                log.info('Coluna %s.%s passou a aceitar NULL', tabela, nome)


def _garantir_utilizador_app(eng_admin):
    """Cria (ou atualiza a senha de) o utilizador do DATABASE_URL só com SELECT/INSERT/UPDATE/DELETE."""
    app_url = make_url(DATABASE_URL)
    utilizador, senha = app_url.username, app_url.password
    if not utilizador or utilizador == eng_admin.url.username:
        log.warning('DATABASE_URL usa o dono do banco: a aplicação tem mais privilégios do que precisa '
                    '(ver configurar_banco_app.py).')
        return
    if not senha:
        raise RuntimeError('DATABASE_URL sem senha para o utilizador da aplicação.')
    q = eng_admin.dialect.identifier_preparer.quote_identifier
    with eng_admin.begin() as con:
        existe = con.exec_driver_sql('SELECT 1 FROM pg_roles WHERE rolname = %(r)s', {'r': utilizador}).scalar()
        acao = 'ALTER' if existe else 'CREATE'
        # O psycopg2 põe a senha como literal com escape; o nome vai entre aspas de identificador
        con.exec_driver_sql(f'{acao} ROLE {q(utilizador)} WITH LOGIN NOSUPERUSER NOCREATEDB '
                            f'NOCREATEROLE NOREPLICATION PASSWORD %(s)s', {'s': senha})
        base = con.exec_driver_sql('SELECT current_database()').scalar()
        for sql in (f'GRANT CONNECT ON DATABASE {q(base)} TO {q(utilizador)}',
                    f'GRANT USAGE ON SCHEMA public TO {q(utilizador)}',
                    f'REVOKE CREATE ON SCHEMA public FROM {q(utilizador)}',
                    f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {q(utilizador)}',
                    f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {q(utilizador)}'):
            con.exec_driver_sql(sql)
    log.info('Utilizador da aplicação %s pronto (só leitura e escrita de dados)', utilizador)


def criar_tabela():
    """Cria as tabelas, aplica as colunas novas e prepara o utilizador da aplicação.
    Com DATABASE_URL_ADMIN usa o dono do banco; sem ele, o próprio DATABASE_URL (como antes)."""
    url_admin = os.environ.get('DATABASE_URL_ADMIN')
    eng = create_engine(url_admin) if url_admin else engine
    try:
        Base.metadata.create_all(eng)
        _migrar(eng)
        if url_admin and eng.dialect.name == 'postgresql':
            _garantir_utilizador_app(eng)
    finally:
        if eng is not engine:
            eng.dispose()


def verificar_ligacao():
    """True se o banco responde (usado em /saude)."""
    try:
        with engine.connect() as con:
            con.exec_driver_sql('SELECT 1')
        return True
    except Exception:
        return False


# ---------- Conversão para dicionários (JSON) ----------
def _teste_para_dict(t):
    return {
        'id': t.id,
        'vaca': t.vaca.brinco,
        'data': t.data.isoformat(),
        'tem_mastite': t.tem_mastite,
        'tetos_afetados': [int(x) for x in t.tetos_afetados.split(',') if x],
        'observacao': t.observacao,
        'operador': t.usuario.nome if t.usuario else None,
        'leituras': [
            {'teto': l.teto, 'temp': l.temp, 'cond': l.cond,
             'suspeito': l.suspeito, 'motivo': l.motivo}
            for l in t.leituras
        ],
    }


# ---------- Escrita ----------
def registrar_teste(brinco, leituras, diagnostico, observacao=None, usuario_id=None):
    """Grava vaca (se nova) + teste + 4 leituras numa única transação."""
    afetados = [str(i + 1) for i, d in enumerate(diagnostico) if d['suspeito']]
    with Session(engine) as sessao:
        vaca = sessao.scalar(select(Vaca).where(Vaca.brinco == brinco))
        if vaca is None:
            vaca = Vaca(brinco=brinco)
            sessao.add(vaca)

        teste = Teste(
            vaca=vaca,
            tem_mastite=bool(afetados),
            tetos_afetados=','.join(afetados),
            observacao=observacao,
            usuario_id=usuario_id,
        )
        for i, (l, d) in enumerate(zip(leituras, diagnostico), start=1):
            teste.leituras.append(Leitura(
                teto=i, temp=l['temp'], cond=l['cond'],
                suspeito=d['suspeito'], motivo=d['motivo'],
            ))
        sessao.add(teste)
        sessao.commit()
        sessao.refresh(teste)
        return _teste_para_dict(teste)


def apagar_teste(teste_id):
    with Session(engine) as sessao:
        teste = sessao.get(Teste, teste_id)
        if teste is None:
            return False
        sessao.delete(teste)
        sessao.commit()
        return True


# ---------- Leitura ----------
def _filtros(brinco=None, suspeitos=None):
    filtros = []
    if brinco:
        filtros.append(Vaca.brinco == brinco)
    if suspeitos is not None:
        filtros.append(Teste.tem_mastite == suspeitos)
    return filtros


def listar_testes(brinco=None, suspeitos=None, limite=20, pagina=1):
    """Testes mais recentes primeiro. Devolve (lista, total)."""
    filtros = _filtros(brinco, suspeitos)
    with Session(engine) as sessao:
        total = sessao.scalar(
            select(func.count(Teste.id)).join(Teste.vaca).where(*filtros)
        )
        consulta = (
            select(Teste).join(Teste.vaca)
            .options(contains_eager(Teste.vaca), selectinload(Teste.leituras),
                     selectinload(Teste.usuario))
            .where(*filtros)
            .order_by(Teste.id.desc())
            .limit(limite).offset((pagina - 1) * limite)
        )
        return [_teste_para_dict(t) for t in sessao.scalars(consulta)], total


def obter_teste(teste_id):
    with Session(engine) as sessao:
        consulta = (
            select(Teste).where(Teste.id == teste_id)
            .options(selectinload(Teste.leituras), selectinload(Teste.vaca),
                     selectinload(Teste.usuario))
        )
        teste = sessao.scalar(consulta)
        return _teste_para_dict(teste) if teste else None


def listar_vacas(limite=1000, pagina=1):
    with Session(engine) as sessao:
        consulta = (
            select(
                Vaca.brinco,
                func.count(Teste.id),
                func.max(Teste.data),
                func.coalesce(func.sum(case((Teste.tem_mastite, 1), else_=0)), 0),
            )
            .outerjoin(Teste).group_by(Vaca.id).order_by(Vaca.brinco)
            .limit(limite).offset((pagina - 1) * limite)
        )
        return [
            {'brinco': b, 'testes': n, 'ultimo_teste': u.isoformat() if u else None,
             'testes_com_suspeita': int(s)}
            for b, n, u, s in sessao.execute(consulta)
        ]


def estatisticas():
    with Session(engine) as sessao:
        total = sessao.scalar(select(func.count(Teste.id)))
        suspeitos = sessao.scalar(select(func.count(Teste.id)).where(Teste.tem_mastite))
        vacas = sessao.scalar(select(func.count(Vaca.id)))
        media_temp, media_cond = sessao.execute(
            select(func.avg(Leitura.temp), func.avg(Leitura.cond))
        ).one()
        por_teto = dict(sessao.execute(
            select(Leitura.teto, func.count()).where(Leitura.suspeito).group_by(Leitura.teto)
        ).all())
        return {
            'vacas': vacas,
            'testes': total,
            'testes_com_suspeita': suspeitos,
            'percentual_suspeita': round(100 * suspeitos / total, 1) if total else 0,
            'temp_media': round(media_temp, 1) if media_temp is not None else None,
            'cond_media': round(media_cond) if media_cond is not None else None,
            'suspeitas_por_teto': {str(t): por_teto.get(t, 0) for t in (1, 2, 3, 4)},
        }


def linhas_csv(brinco=None):
    """Uma linha por leitura, para exportação. Gerador: lê do banco aos blocos, sem carregar tudo."""
    with Session(engine) as sessao:
        consulta = (
            select(Teste.id, Vaca.brinco, Teste.data, Leitura.teto, Leitura.temp,
                   Leitura.cond, Leitura.suspeito, Leitura.motivo)
            .join(Leitura, Leitura.teste_id == Teste.id)
            .join(Vaca, Vaca.id == Teste.vaca_id)
            .where(*_filtros(brinco))
            .order_by(Teste.id, Leitura.teto)
            .execution_options(yield_per=500)
        )
        for tid, b, d, teto, temp, cond, susp, motivo in sessao.execute(consulta):
            yield (tid, b, d.astimezone().strftime('%Y-%m-%d %H:%M:%S'), teto, temp, cond,
                   'sim' if susp else 'nao', motivo or '')


if __name__ == '__main__':
    criar_tabela()
    print('Tabelas criadas.')