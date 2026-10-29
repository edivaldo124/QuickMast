// Histórico de uma vaca: só lê GET /api/vacas/<brinco>/testes (mais recente primeiro).
const BRINCO = document.body.dataset.brinco;
const FALHA = 'Erro ao carregar o histórico';

// Resumo por cima da linha do tempo: quantos testes, quantos com suspeita e a data do último
function resumir(testes) {
    if (!testes.length) return;
    const suspeitos = testes.filter(t => t.tem_mastite).length;
    document.getElementById('resumoVaca').replaceChildren(
        criar('span', 'resumo__item', testes.length + (testes.length === 1 ? ' teste' : ' testes')),
        criar('span', 'resumo__item' + (suspeitos ? ' resumo__item--suspeita' : ''), suspeitos + ' com suspeita'),
        criar('span', 'resumo__item', 'Último: ' + formatarData(testes[0].data))
    );
}

async function carregar() {
    const linha = document.getElementById('linhaTempo');
    try {
        const r = await fetch('/api/vacas/' + encodeURIComponent(BRINCO) + '/testes');
        const corpo = await r.json();
        if (!r.ok) throw new Error(corpo.erro || FALHA);

        linha.replaceChildren(...corpo.testes.map(t => {
            const evento = criar('li', 'evento');
            evento.append(
                icone('evento__marcador ' + (t.tem_mastite ? 'ic--suspeita' : 'ic--sadio')),
                itemHistorico(t, false)
            );
            return evento;
        }));
        primeiraEntrada(linha);
        resumir(corpo.testes);
    } catch (e) {
        linha.replaceChildren();   // sai o esqueleto
        // Mensagem da API (ex.: "vaca sem testes"); falha de rede ou de JSON dá o texto genérico
        banner(document.getElementById('mensagem'), 'alerta', e.constructor === Error ? e.message : FALHA);
    }
}

carregar();
