// Histórico de uma vaca: só lê GET /api/vacas/<brinco>/testes (mais recente primeiro).
const BRINCO = document.body.dataset.brinco;
const FALHA = 'Erro ao carregar o histórico';

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
    } catch (e) {
        // Mensagem da API (ex.: "vaca sem testes"); falha de rede ou de JSON dá o texto genérico
        banner(document.getElementById('mensagem'), 'alerta', e.constructor === Error ? e.message : FALHA);
    }
}

carregar();
