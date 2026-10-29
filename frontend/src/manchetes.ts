// As manchetes do hero. O scroll do trilho (0 a 1) é dividido em partes iguais entre elas,
// e a cena 3D segue as mesmas partes (three/UbereScene.tsx).
// Linhas curtas (até ~13 caracteres): o título chega a ~120 px no computador.
// O texto descreve o que o app faz hoje (servicos/diagnostico.py, ubere.js); sem números de
// limiares, que ainda vão ser calibrados.
export type Manchete = {
  sobretitulo: string
  titulo: [string, string]
  detalhe: string
}

export const MANCHETES: Manchete[] = [
  {
    sobretitulo: 'Detetor rápido de mastite',
    titulo: ['Quatro tetos.', 'Uma sonda.'],
    detalhe: 'A sonda mede a condutividade do leite de cada teto, pela ordem 1, 2, 3, 4.',
  },
  {
    sobretitulo: 'Leitura ao vivo',
    titulo: ['Ao vivo,', 'teto a teto.'],
    detalhe: 'Com a sonda no teto, o valor atualiza a cada 2 segundos. Um toque captura a amostra.',
  },
  {
    sobretitulo: 'Diagnóstico na hora',
    titulo: ['Um teto', 'contra três.'],
    detalhe: 'Se a condutividade de um teto fica acima da dos outros três, ou da referência, o alerta acende.',
  },
  {
    sobretitulo: 'Histórico e painel',
    titulo: ['Cada vaca,', 'um histórico.'],
    detalhe: 'Cada teste fica guardado pelo brinco, com as suspeitas por teto e o relatório em CSV.',
  },
]
