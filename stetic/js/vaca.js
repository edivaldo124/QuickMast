// Histórico de uma vaca: só lê GET /api/vacas/<brinco>/testes (mais recente primeiro).
const BRINCO = document.body.dataset.brinco;
const FALHA = 'Erro ao carregar o histórico';
const $ = id => document.getElementById(id);
const POR_PAGINA = 10;   // testes na linha do tempo; "Ver mais testes" acrescenta outros tantos
const TENDENCIA = 20;    // testes nas barras de cada teto
const ESCALA_MIN = 80;   // pontos de condutividade: numa escala mais curta, o ruído pareceria uma subida

// Os tetos pela posição no úbere (ORDEM_UBERE, de componentes.js): AE | AD em cima, PE | PD em baixo
const NOMES = { 1: 'anterior direito', 2: 'anterior esquerdo', 3: 'posterior direito', 4: 'posterior esquerdo' };
const TETOS = ORDEM_UBERE.map(n => ({ n, sigla: SIGLAS[n], nome: NOMES[n] }));

const leituraDe = (t, n) => t.leituras.find(l => l.teto === n);
const rotulo = teto => teto.sigla + ' · T' + teto.n;
const temTemp = l => l.temp !== null && l.temp !== undefined;

// Resumo por cima de tudo: quantos testes, quantos com suspeita e a data do último
function resumir(testes) {
    if (!testes.length) return;
    const suspeitos = testes.filter(t => t.tem_mastite).length;
    $('resumoVaca').replaceChildren(
        criar('span', 'resumo__item', testes.length + (testes.length === 1 ? ' teste' : ' testes')),
        criar('span', 'resumo__item' + (suspeitos ? ' resumo__item--suspeita' : ''), suspeitos + ' com suspeita'),
        criar('span', 'resumo__item', 'Último: ' + formatarData(testes[0].data))
    );
}

// ---------- Condutividade por teto: o último valor, uma barra por teste e a faixa ----------
function cartaoTeto(teto, leituras, altura) {
    const ultima = leituras[leituras.length - 1];
    const suspeito = Boolean(ultima && ultima.suspeito);
    const cartao = criar('article', 'cartao teto-vaca' + (suspeito ? ' teto-vaca--suspeita' : ''));
    cartao.setAttribute('aria-label', 'Teto ' + teto.n + ', ' + teto.nome);

    const cabeca = criar('p', 'teto-vaca__rotulo', rotulo(teto));
    if (suspeito) cabeca.append(icone('ic--suspeita'));

    const valor = criar('p', 'teto-vaca__valor num', ultima ? String(ultima.cond) : '--');
    if (suspeito) valor.append(criar('span', 'sr-only', ' (suspeito no último teste)'));

    // As barras repetem os números de baixo em forma de desenho: o leitor de ecrã salta-as
    const barras = criar('div', 'barras');
    barras.setAttribute('aria-hidden', 'true');
    barras.append(...leituras.map(l => {
        const barra = criar('span', 'barras__barra' + (l.suspeito ? ' barras__barra--suspeita' : ''));
        barra.style.setProperty('--h', altura(l.cond).toFixed(1) + '%');
        return barra;
    }));

    cartao.append(cabeca, valor, barras);

    const conds = leituras.map(l => l.cond);
    const min = Math.min(...conds), max = Math.max(...conds);
    const faixa = [];
    if (min !== max) faixa.push('de ' + min + ' a ' + max);
    if (ultima && temTemp(ultima)) faixa.push(ultima.temp.toFixed(1) + ' °C');
    if (faixa.length) cartao.append(criar('p', 'teto-vaca__detalhe', faixa.join(' · ')));

    const suspeitas = leituras.filter(l => l.suspeito).length;
    if (suspeitas) cartao.append(criar('p', 'teto-vaca__suspeitas', suspeitas + (suspeitas === 1 ? ' suspeita' : ' suspeitas')));
    return cartao;
}

function tetosDaVaca(testes) {
    const grade = $('tetosVaca');
    // Com um só teste não há tendência, e os números já estão no cartão desse teste
    if (testes.length < 2) return $('secaoTetos').classList.add('escondido');
    const recentes = testes.slice(0, TENDENCIA).reverse();   // do mais antigo ao último
    const conds = recentes.flatMap(t => t.leituras.map(l => l.cond));

    // Uma só escala para os 4 tetos: um teto que lê acima dos outros vê-se logo
    const topo = Math.max(...conds);
    const fundo = Math.min(...conds, topo - ESCALA_MIN);
    const altura = cond => 12 + ((cond - fundo) / (topo - fundo)) * 88;

    grade.replaceChildren(...TETOS.map(teto =>
        cartaoTeto(teto, recentes.map(t => leituraDe(t, teto.n)).filter(Boolean), altura)
    ));
    grade.setAttribute('aria-busy', 'false');
    primeiraEntrada(grade);
    $('periodoTetos').textContent = '· ' + (recentes.length === 1 ? 'último teste' : 'últimos ' + recentes.length + ' testes');
}

// ---------- Linha do tempo: cada teste com as 4 leituras e o motivo de cada suspeita ----------
function cartaoTeste(t) {
    const cartao = criar('article', 'cartao teste');

    const quando = criar('div');
    quando.append(
        criar('p', 'teste__data num', formatarData(t.data)),
        criar('p', 'teste__operador', t.operador || '-')
    );
    const topo = criar('div', 'teste__topo');
    topo.append(quando, seloTeste(t));

    // As 4 leituras na posição do úbere; o teto suspeito fica a vermelho
    const grade = criar('dl', 'leituras');
    grade.append(...TETOS.map(teto => {
        const l = leituraDe(t, teto.n);
        const celula = criar('div', 'leitura' + (l && l.suspeito ? ' leitura--suspeita' : ''));
        const valor = criar('dd', 'leitura__valor num', l ? String(l.cond) : '--');
        if (l && l.suspeito) valor.append(criar('span', 'sr-only', ' (suspeito)'));
        celula.append(criar('dt', 'leitura__teto', rotulo(teto)), valor);
        if (l && temTemp(l)) celula.append(criar('dd', 'leitura__temp num', l.temp.toFixed(1) + ' °C'));
        return celula;
    }));

    cartao.append(topo, criar('p', 'leituras__titulo', 'Condutividade'), grade);

    const suspeitas = t.leituras.filter(l => l.suspeito).sort((a, b) => a.teto - b.teto);
    if (suspeitas.length) {
        const motivos = criar('ul', 'teste__motivos');
        motivos.append(...suspeitas.map(l => criar('li', null, textoTetos([l.teto]) + ': ' + (l.motivo || 'suspeita'))));
        cartao.append(motivos);
    }
    if (t.observacao) cartao.append(criar('p', 'teste__observacao', t.observacao));
    return cartao;
}

function linhaDoTempo(testes) {
    const linha = $('linhaTempo'), mais = $('maisTestes');
    const evento = t => {
        const li = criar('li', 'evento');
        li.append(icone('evento__marcador ' + (t.tem_mastite ? 'ic--suspeita' : 'ic--sadio')), cartaoTeste(t));
        return li;
    };

    let mostrados = 0;
    const maisEventos = () => {
        const fatia = testes.slice(mostrados, mostrados + POR_PAGINA).map(evento);
        if (mostrados === 0) { linha.replaceChildren(...fatia); primeiraEntrada(linha); }
        else linha.append(...fatia);
        mostrados += fatia.length;
        mais.classList.toggle('escondido', mostrados >= testes.length);
    };
    mais.addEventListener('click', maisEventos);
    maisEventos();
}

async function carregar() {
    try {
        const r = await fetch('/api/vacas/' + encodeURIComponent(BRINCO) + '/testes');
        const corpo = await r.json();
        if (!r.ok) throw new Error(corpo.erro || FALHA);

        resumir(corpo.testes);
        tetosDaVaca(corpo.testes);
        linhaDoTempo(corpo.testes);
    } catch (e) {
        // Sem testes não há tetos nem linha do tempo: fica só a mensagem
        $('secaoTetos').classList.add('escondido');
        $('secaoTestes').classList.add('escondido');
        // Mensagem da API (ex.: "vaca sem testes"); falha de rede ou de JSON dá o texto genérico
        banner($('mensagem'), 'alerta', e.constructor === Error ? e.message : FALHA);
    }
}

carregar();
