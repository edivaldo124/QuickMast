# Importar os modelos aqui garante que o SQLAlchemy os conhece todos
# antes de criar as tabelas.
from modelos.base import Base
from modelos.usuario import Usuario
from modelos.vaca import Vaca
from modelos.teste import Teste
from modelos.leitura import Leitura

__all__ = ['Base', 'Usuario', 'Vaca', 'Teste', 'Leitura']

