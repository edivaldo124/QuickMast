from sqlalchemy import select, func, update

from sqlalchemy.orm import Session

from dao.banco import engine
from modelos.usuario import Usuario


def _para_dict(u, com_hash=False):
    d = {
        'id': u.id, 'nome': u.nome, 'email': u.email, 'perfil': u.perfil,
        'ativo': u.ativo, 'criado_em': u.criado_em.isoformat(),
    }
    if com_hash:
        d['senha_hash'] = u.senha_hash
    return d


def criar_usuario(nome, email, senha_hash, perfil='operador'):
    """Cria o utilizador. O primeiro de todos passa a ser admin (arranque do sistema)."""
    with Session(engine) as sessao:
        if sessao.scalar(select(func.count(Usuario.id))) == 0:
            perfil = 'admin'
        u = Usuario(nome=nome, email=email, senha_hash=senha_hash, perfil=perfil)
        sessao.add(u)
        sessao.commit()
        sessao.refresh(u)
        return _para_dict(u)


def obter_por_email(email):
    """Inclui o hash da senha: usar só para validar o login."""
    with Session(engine) as sessao:
        u = sessao.scalar(select(Usuario).where(Usuario.email == email))
        return _para_dict(u, com_hash=True) if u else None


def obter_por_id(usuario_id):
    with Session(engine) as sessao:
        u = sessao.get(Usuario, usuario_id)
        return _para_dict(u) if u else None


def listar_usuarios():
    with Session(engine) as sessao:
        return [_para_dict(u) for u in sessao.scalars(select(Usuario).order_by(Usuario.nome))]


def contar_admins_ativos():
    with Session(engine) as sessao:
        return sessao.scalar(
            select(func.count(Usuario.id)).where(Usuario.perfil == 'admin', Usuario.ativo)
        )


def atualizar_usuario(usuario_id, perfil=None, ativo=None):
    with Session(engine) as sessao:
        u = sessao.get(Usuario, usuario_id)
        if u is None:
            return None
        if perfil is not None:
            u.perfil = perfil
        if ativo is not None:
            u.ativo = ativo
        sessao.commit()
        sessao.refresh(u)
        return _para_dict(u)

