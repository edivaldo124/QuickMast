// Painel de estatísticas: só lê GET /api/estatisticas, /api/vacas e /api/testes.
const $ = id => document.getElementById(id);
const POR_PAGINA = 10;

const NOMES = {
    1: 'Anterior Direito',
    2: 'Anterior Esquerdo',
    3: 'Posterior Direito',
    4: 'Posterior Esquerdo'
};

// Texto branco ou escuro, o que contrastar mais com o vermelho de suspeita (#C62828)
// misturado com o fundo (#F4F4F4) na opacidade dada.
function corTexto(alfa) {
    const canal = c => {
        const v = (c * alfa + 244 * (1 - alfa)) / 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    const lum = 0.2126 * canal(198) + 0.7152 * canal(40) + 0.0722 * canal(40);
    const contrasteBranco = 1.05 / (lum + 0.05);
    const contrasteEscuro = (lum + 0.05) / 0.0652;   // #212121
    return contrasteBranco >= contrasteEscuro ? 'var(--texto-branco)' : 'var(--texto-principal)';
}

// Detalhe do teto tocado: quantas suspeitas e que parte do total são dele
function mostrarDetalhe(escolhido, n, total) {
    document.querySelectorAll('.mapa__teto').forEach(el => el.setAttribute('aria-pressed', String(el === escolhido)));
    const detalhe = $('detalheTeto');
    const nome = criar('strong', null, 'Teto ' + escolhido.dataset.teto + ' (' + NOMES[escolhido.dataset.teto] + ')');
    const parte = total ? ', ' + Math.round((n / total) * 100) + '% de todas as suspeitas.' : '.';
    detalhe.replaceChildren(nome, ': ' + n + (n === 1 ? ' suspeita' : ' suspeitas') + parte);
}

async function carregar() {
    const painel = document.querySelector('.painel');
    try {
        const r = await fetch('/api/estatisticas');
        const s = await r.json();
        if (!r.ok) throw new Error(s.erro);
        painel.setAttribute('aria-busy', 'false');

        if (s.temp_media === null) $('tempMedia').textContent = '--';
        else contar($('tempMedia'), s.temp_media, v => v.toFixed(1) + ' °C');
        if (s.cond_media === null) $('condMedia').textContent = '--';
        else contar($('condMedia'), s.cond_media);

        // Intensidade relativa ao teto com mais suspeitas (o CSS anima a --alfa, um teto de cada vez)
        const contagens = Object.values(s.suspeitas_por_teto);
        const max = Math.max(...contagens);
        const total = contagens.reduce((a, b) => a + b, 0);
        document.querySelectorAll('.mapa__teto').forEach((el, i) => {
            const n = s.suspeitas_por_teto[el.dataset.teto];
            const alfa = 0.12 + (max ? n / max : 0) * 0.88;
            el.style.setProperty('--i', i);
            el.style.setProperty('--alfa', alfa.toFixed(2));
            el.style.setProperty('--cor-texto', corTexto(alfa));
            contar(el.querySelector('.mapa__numero'), n);
            el.addEventListener('click', () => mostrarDetalhe(el, n, total));
        });
        $('escalaMax').textContent = max;
    } catch (e) {
        painel.setAttribute('aria-busy', 'false');
        banner($('mensagem'), 'alerta', 'Erro ao carregar as estatísticas');
    }
}

// ---------- Listas: as vacas (GET /api/vacas) e os testes (GET /api/testes) ----------
// Cada item abre o histórico da vaca. Ver mais acrescenta mais POR_PAGINA itens.
// Uma vaca: o brinco, quando foi o último teste e quantos tem; à direita, quantos deram suspeita
function itemVaca(v) {
    const n = v.testes_com_suspeita;
    const item = criar('a', 'item' + (n ? ' item--suspeita' : ''));
    item.href = '/vacas/' + encodeURIComponent(v.brinco);
    item.append(
        brinco(v.brinco, 'item__vaca'),
        v.ultimo_teste ? dataItem(v.ultimo_teste) : criar('span', 'item__data', 'Sem testes'),
        criar('span', 'item__operador', v.testes + (v.testes === 1 ? ' teste' : ' testes'))
    );
    if (v.testes) {
        const estado = criar('span', 'item__estado');
        if (n) estado.append(criar('span', 'item__contagem', n), criar('span', null, n === 1 ? 'suspeita' : 'suspeitas'));
        else estado.append(criar('span', null, 'Sem suspeitas'));
        item.append(estado);
    }
    return item;
}

// Troca os esqueletos por um aviso (erro ou lista vazia)
function avisarLista(lista, tipo, mensagem) {
    const li = criar('li');
    if (tipo) banner(li, tipo, mensagem);
    else { li.className = 'procura__vazio'; li.textContent = mensagem; }
    lista.replaceChildren(li);
}

function acrescentar(lista, itens, primeira) {
    const lis = itens.map(conteudo => {
        const li = criar('li');
        li.append(conteudo);
        return li;
    });
    if (primeira) { lista.replaceChildren(...lis); primeiraEntrada(lista); }
    else lista.append(...lis);
}

async function carregarVacas() {
    const lista = $('listaVacas'), mais = $('maisVacas');
    try {
        const r = await fetch('/api/vacas');
        const vacas = await r.json();
        if (!r.ok) throw new Error();
        $('totalVacas').textContent = '· ' + vacas.length;
        if (!vacas.length) return avisarLista(lista, null, 'Ainda não há vacas registadas.');

        let mostradas = 0;
        const maisItens = () => {
            const fatia = vacas.slice(mostradas, mostradas + POR_PAGINA);
            acrescentar(lista, fatia.map(itemVaca), mostradas === 0);
            mostradas += fatia.length;
            mais.classList.toggle('escondido', mostradas >= vacas.length);
        };
        mais.addEventListener('click', maisItens);
        maisItens();
    } catch (e) {
        avisarLista(lista, 'alerta', 'Erro ao carregar as vacas');
    }
}

async function carregarTestes() {
    const lista = $('listaTestes'), mais = $('maisTestes');
    let pagina = 0;
    async function maisItens() {
        mais.disabled = true;
        try {
            const r = await fetch('/api/testes?limite=' + POR_PAGINA + '&pagina=' + (pagina + 1));
            const dados = await r.json();
            if (!r.ok) throw new Error();
            acrescentar(lista, dados.testes.map(t => itemHistorico(t, true)), pagina === 0);
            pagina = dados.pagina;
            $('totalTestes').textContent = '· ' + dados.total;
            if (!dados.total) avisarLista(lista, null, 'Ainda não há testes registados.');
            mais.classList.toggle('escondido', pagina * dados.limite >= dados.total);
        } catch (e) {
            // na 1.ª página o aviso ocupa o lugar dos esqueletos; depois vai para o banner do topo
            if (pagina === 0) avisarLista(lista, 'alerta', 'Erro ao carregar os testes');
            else banner($('mensagem'), 'alerta', 'Não foi possível carregar mais testes');
        } finally {
            mais.disabled = false;
        }
    }
    mais.addEventListener('click', maisItens);
    maisItens();
}

carregar();
carregarVacas();
carregarTestes();
