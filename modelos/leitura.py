from sqlalchemy import Integer, String, Float, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from modelos.base import Base


class Leitura(Base):
    """A leitura de um teto dentro de um teste."""
    __tablename__ = 'leituras'
    __table_args__ = (
        UniqueConstraint('teste_id', 'teto', name='uq_leitura_teste_teto'),
        CheckConstraint('teto BETWEEN 1 AND 4', name='ck_leitura_teto'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teste_id: Mapped[int] = mapped_column(ForeignKey('testes.id', ondelete='CASCADE'), index=True)
    teto: Mapped[int] = mapped_column(Integer)
    temp: Mapped[float | None] = mapped_column(Float, nullable=True)   # a placa atual não mede temperatura
    cond: Mapped[int] = mapped_column(Integer)
    suspeito: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo: Mapped[str | None] = mapped_column(String(100), nullable=True)

    teste: Mapped['Teste'] = relationship(back_populates='leituras')
