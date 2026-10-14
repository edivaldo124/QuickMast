from datetime import datetime

from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from modelos.base import Base


class Teste(Base):
    """Uma sessão de medição: os 4 tetos de uma vaca + o diagnóstico."""
    __tablename__ = 'testes'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vaca_id: Mapped[int] = mapped_column(ForeignKey('vacas.id', ondelete='CASCADE'), index=True)
    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    tem_mastite: Mapped[bool] = mapped_column(Boolean, default=False)
    tetos_afetados: Mapped[str] = mapped_column(String(20), default='')   # ex.: "1,3"
    observacao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True, index=True
    )

    vaca: Mapped['Vaca'] = relationship(back_populates='testes')
    usuario: Mapped['Usuario | None'] = relationship()
    leituras: Mapped[list['Leitura']] = relationship(
        back_populates='teste', cascade='all, delete-orphan', order_by='Leitura.teto'
    )

