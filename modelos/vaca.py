from datetime import datetime

from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from modelos.base import Base


class Vaca(Base):
    """Uma vaca, identificada pelo brinco (único)."""
    __tablename__ = 'vacas'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brinco: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    testes: Mapped[list['Teste']] = relationship(
        back_populates='vaca', cascade='all, delete-orphan', order_by='Teste.id'
    )

