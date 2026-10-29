// Cores em hex para o 3D: o THREE.Color não lê variáveis CSS.
// Espelham stetic/css/quickmast.css (1. VARIÁVEIS) e landing.css; ao mudar uma, mudar a outra.
export const cores = {
  marca: '#2E7D32',       // --botao-verde: a placa do logo
  placaNoite: '#17251B',  // a placa antes de "virar" logo, no fundo escuro da landing
  tetoVazio: '#E6EBE5',   // teto ainda não medido
  aLer: '#1E88E5',        // --teto-a-ler
  sadio: '#2E7D32',       // --teto-sadio
  suspeita: '#C62828',    // --teto-suspeita
  branco: '#FFFFFF',
  aco: '#C9D1CB',         // haste da sonda
  pega: '#1C231E',        // --texto-principal: pega da sonda
} as const
