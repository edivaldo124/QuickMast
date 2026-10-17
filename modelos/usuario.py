from datetime import datetime

from sqlalchemy import Integer, String, Boolean, DateTime, CheckConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from modelos.base import Base

# operador: mede | veterinario: mede e (futuramente) confirma | admin: gere tudo
PERFIS = ('operador', 'veterinario', 'admin')


class Usuario(Base):
    __tablename__ = 'usuarios'
    __table_args__ = (
        CheckConstraint("perfil IN ('operador', 'veterinario', 'admin')", name='ck_usuario_perfil'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))   # nunca a senha em texto
    perfil: Mapped[str] = mapped_column(String(20), default='operador')
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Vai no cookie de sessão; aumentar este número (logout, troca de senha) invalida as cópias antigas
    sessao_versao: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    # Verificação em dois passos (obrigatória para admin): segredo TOTP e último passo usado (anti-replay)
    totp_segredo: Mapped[str | None] = mapped_column(String(32), nullable=True)
    totp_ultimo_passo: Mapped[int | None] = mapped_column(Integer, nullable=True)

