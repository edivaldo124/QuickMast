import os

from sqlalchemy import create_engine, select, func, case
from sqlalchemy.orm import Session, selectinload, contains_eager

from modelos import Base, Vaca, Teste, Leitura

# Endereço do PostgreSQL, vindo da variável de ambiente DATABASE_URL (.env).
# Formato: postgresql+psycopg2://utilizador:senha@servidor:porta/base
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL não definida: copie .env.example para .env e preencha.')

# pool_pre_ping testa a ligação antes de a usar (evita erros se o banco reiniciar)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def criar_tabela():
    Base.metadata.create_all(engine)


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


def listar_vacas():
    with Session(engine) as sessao:
        consulta = (
            select(
                Vaca.brinco,
                func.count(Teste.id),
                func.max(Teste.data),
                func.coalesce(func.sum(case((Teste.tem_mastite, 1), else_=0)), 0),
            )
            .outerjoin(Teste).group_by(Vaca.id).order_by(Vaca.brinco)
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
    """Uma linha por leitura, para exportação."""
    with Session(engine) as sessao:
        consulta = (
            select(Teste.id, Vaca.brinco, Teste.data, Leitura.teto, Leitura.temp,
                   Leitura.cond, Leitura.suspeito, Leitura.motivo)
            .join(Leitura, Leitura.teste_id == Teste.id)
            .join(Vaca, Vaca.id == Teste.vaca_id)
            .where(*_filtros(brinco))
            .order_by(Teste.id, Leitura.teto)
        )
        return [
            (tid, b, d.astimezone().strftime('%Y-%m-%d %H:%M:%S'), teto, temp, cond,
             'sim' if susp else 'nao', motivo or '')
            for tid, b, d, teto, temp, cond, susp, motivo in sessao.execute(consulta)
        ]


if __name__ == '__main__':
    criar_tabela()
    print('Tabelas criadas.')