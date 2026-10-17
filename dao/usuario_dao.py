from sqlalchemy import select, func, update, or_
from sqlalchemy.orm import Session

from dao.banco import engine
from modelos.usuario import Usuario

# Campos que nunca saem na API nem nos templates (ver publico())
_INTERNOS = ('senha_hash', 'sessao_versao', 'totp_segredo', 'totp_ultimo_passo')


def _para_dict(u, interno=False):
    d = {
        'id': u.id, 'nome': u.nome, 'email': u.email, 'perfil': u.perfil,
        'ativo': u.ativo, 'criado_em': u.criado_em.isoformat(),
        'mfa_ativo': u.totp_segredo is not None,
    }
    if interno:
        d.update({campo: getattr(u, campo) for campo in _INTERNOS})
    return d


def publico(d):
    """Tira os campos internos de um dicionário vindo de interno=True."""
    return {k: v for k, v in d.items() if k not in _INTERNOS}


def criar_usuario(nome, email, senha_hash, perfil='operador'):
    """Cria o utilizador. O admin inicial vem só do .env (garantir_admin), nunca do registo público."""
    with Session(engine) as sessao:
        u = Usuario(nome=nome, email=email, senha_hash=senha_hash, perfil=perfil)
        sessao.add(u)
        sessao.commit()
        sessao.refresh(u)
        return _para_dict(u, interno=True)


def obter_por_email(email):
    """Inclui o hash da senha e o segredo MFA: usar só para validar o login."""
    with Session(engine) as sessao:
        u = sessao.scalar(select(Usuario).where(Usuario.email == email))
        return _para_dict(u, interno=True) if u else None


def obter_por_id(usuario_id, interno=False):
    with Session(engine) as sessao:
        u = sessao.get(Usuario, usuario_id)
        return _para_dict(u, interno) if u else None


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
            if not ativo:
                u.sessao_versao += 1   # ao reativar, cookies antigos já não servem
            u.ativo = ativo
        sessao.commit()
        sessao.refresh(u)
        return _para_dict(u)


def encerrar_sessoes(usuario_id):
    """Invalida todos os cookies de sessão do utilizador. Devolve a nova versão."""
    with Session(engine) as sessao:
        versao = sessao.scalar(
            update(Usuario).where(Usuario.id == usuario_id)
            .values(sessao_versao=Usuario.sessao_versao + 1)
            .returning(Usuario.sessao_versao)
        )
        sessao.commit()
        return versao


def alterar_senha(usuario_id, senha_hash):
    """Troca o hash e encerra as outras sessões. Devolve a nova versão da sessão."""
    with Session(engine) as sessao:
        versao = sessao.scalar(
            update(Usuario).where(Usuario.id == usuario_id)
            .values(senha_hash=senha_hash, sessao_versao=Usuario.sessao_versao + 1)
            .returning(Usuario.sessao_versao)
        )
        sessao.commit()
        return versao


def ativar_mfa(usuario_id, segredo, passo):
    """Guarda o segredo TOTP confirmado e encerra as outras sessões. Devolve a nova versão."""
    with Session(engine) as sessao:
        versao = sessao.scalar(
            update(Usuario).where(Usuario.id == usuario_id, Usuario.totp_segredo.is_(None))
            .values(totp_segredo=segredo, totp_ultimo_passo=passo,
                    sessao_versao=Usuario.sessao_versao + 1)
            .returning(Usuario.sessao_versao)
        )
        sessao.commit()
        return versao   # None se já estava ativa (dois pedidos ao mesmo tempo)


def usar_passo_totp(usuario_id, passo):
    """Marca o código como usado. False se esse passo (ou um posterior) já foi usado: anti-replay atómico."""
    with Session(engine) as sessao:
        r = sessao.execute(
            update(Usuario)
            .where(Usuario.id == usuario_id,
                   or_(Usuario.totp_ultimo_passo.is_(None), Usuario.totp_ultimo_passo < passo))
            .values(totp_ultimo_passo=passo)
        )
        sessao.commit()
        return r.rowcount == 1


def redefinir_mfa(email):
    """Apaga o segredo MFA (telemóvel perdido). O admin volta a configurá-lo no próximo login."""
    with Session(engine) as sessao:
        r = sessao.execute(
            update(Usuario).where(Usuario.email == email)
            .values(totp_segredo=None, totp_ultimo_passo=None,
                    sessao_versao=Usuario.sessao_versao + 1)
        )
        sessao.commit()
        return r.rowcount == 1
