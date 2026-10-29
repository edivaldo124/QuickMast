// O diagnóstico é calculado no servidor (servicos/diagnostico.py).
const NOMES = {
    1: 'Anterior Direito',
    2: 'Anterior Esquerdo',
    3: 'Posterior Direito',
    4: 'Posterior Esquerdo'
};

// Texto de cada estado, igual à legenda (lido pelos leitores de ecrã)
const ESTADOS = {
    'nao-medido': 'Não medido',
    'a-ler': 'A ler',
    'sadio': 'Sadio',
    'mastite': 'Suspeita'
};

// ---------- Estado do teste ----------
let vaca = '';
let tetoAtual = 0;          // 0 = nenhum teste em curso
let leituras = {};          // {1: {temp, cond}, 2: ...}; temp só vem se a placa a medir
let lendoAoVivo = false;    // evita pedidos /read sobrepostos
let timerVivo = null;
let capturando = false;     // uma captura de cada vez: a placa só atende um pedido

// ---------- Elementos da página ----------
const $ = id => document.getElementById(id);

// A placa atual só mede a condutividade: o /read pode vir sem temp
const temTemp = d => typeof d.temp === 'number';

// Abaixo disto a sonda está fora do leite (o mesmo LEITURA_MINIMA do firmware)
const LEITURA_MINIMA = 50;

// O brinco como o servidor o grava (_normalizar_brinco em blueprints/testes.py): "br 102" -> "BR-102"
const normalizarBrinco = b => b.replace(/[\s_-]+/g, '-').replace(/^-+|-+$/g, '').toUpperCase();

function elTeto(n) {
    return document.querySelector('.teto[data-teto="' + n + '"]');
}

function mudarEstado(teto, estado) {
    teto.classList.remove('nao-medido', 'a-ler', 'sadio', 'mastite', 'capturado');
    teto.classList.add(estado);
    teto.querySelector('.teto__estado').textContent = ESTADOS[estado];
}

// Mostra só os blocos da fase: 'vaca', 'medir' ou 'resultado' (ver data-fases no HTML)
function mostrarFase(fase) {
    document.body.dataset.fase = fase;
    // Só enquanto se mede é que os tetos se tocam (para escolher qual capturar)
    document.querySelectorAll('.teto').forEach(t => {
        if (fase === 'medir') {
            t.tabIndex = 0;
            t.setAttribute('role', 'button');
        } else {
            t.removeAttribute('tabindex');
            t.removeAttribute('role');
        }
    });
}

// Botão grande no estado "Carregando" (spinner + texto) ou de volta ao normal
function carregando(btn, sim, rotulo) {
    btn.disabled = sim;
    btn.setAttribute('aria-busy', String(sim));
    btn.textContent = rotulo;
}

// Pede uma leitura ao servidor (/read), que a vai buscar à placa.
// Se falhar, o erro traz a explicação do servidor (ex.: placa não encontrada na rede).
async function lerSensor() {
    let r = null;
    let d = {};
    try {
        r = await fetch('/read');
        d = (await r.json()) || {};
    } catch (e) {
        // sem resposta do servidor, ou uma que não é JSON (ex.: /read desligado)
    }
    if (!r || !r.ok || typeof d.cond !== 'number') {
        throw new Error(d.erro || 'Erro de comunicação com o servidor/placa.');
    }
    return d;
}

// ---------- Leitura em tempo real (a cada 2 s) ----------
// Mini-gráfico: as últimas 20 condutividades do teto em curso, da mais antiga (esquerda) à mais recente
const vivo = [];
function desenharVivo(cond) {
    if (cond !== undefined) {
        vivo.push(cond);
        if (vivo.length > 20) vivo.shift();
    }
    if (vivo.length < 2) {
        $('vivoLinha').setAttribute('points', '');
        return;
    }
    const min = Math.min(...vivo);
    const max = Math.max(...vivo);
    const meio = (min + max) / 2;
    const faixa = Math.max(max - min, 30);   // o ruído de poucos pontos não vira montanha
    $('vivoLinha').setAttribute('points', vivo.map((v, i) =>
        (i / (vivo.length - 1) * 100).toFixed(1) + ',' + (16 - ((v - meio) / faixa) * 24).toFixed(1)
    ).join(' '));
}

async function lerAoVivo() {
    if (lendoAoVivo || tetoAtual === 0) return;
    lendoAoVivo = true;
    try {
        const d = await lerSensor();
        $('vivoTemp').textContent = temTemp(d) ? d.temp.toFixed(1) : '--';
        $('vivoCond').textContent = d.cond;
        desenharVivo(d.cond);
    } catch (e) {
        $('vivoTemp').textContent = '--';
        $('vivoCond').textContent = '--';
    }
    lendoAoVivo = false;
}

function iniciarAoVivo() {
    pararAoVivo();
    lerAoVivo();
    timerVivo = setInterval(lerAoVivo, 2000);
}

function pararAoVivo() {
    if (timerVivo) clearInterval(timerVivo);
    timerVivo = null;
}

// ---------- Captura por teto ----------
// Sem botão na placa, é aqui que se captura: tocar num teto escolhe-o, "Capturar teto N" lê a sonda
// e passa ao próximo que ainda falta (qualquer ordem; capturar de novo substitui a leitura).
// Com os 4 tetos medidos, o teste é gravado.
const rotuloCapturar = n => 'Capturar teto ' + n;

// O teto escolhido ganha o contorno âmbar (tetoAtual 0 = nenhum)
function marcarAtivo() {
    document.querySelectorAll('.teto').forEach(t => {
        const ativo = Number(t.dataset.teto) === tetoAtual;
        t.classList.toggle('ativo', ativo);
        if (ativo) t.setAttribute('aria-current', 'true');
        else t.removeAttribute('aria-current');
    });
}

function mostrarPasso() {
    $('instrucao').textContent =
        'Insira a sonda no Teto ' + tetoAtual + ' (' + NOMES[tetoAtual] + ')'
        + (leituras[tetoAtual] ? ': já medido, capturar de novo substitui a leitura' : '');
    $('progressoTexto').textContent = Object.keys(leituras).length + ' de 4 medidos';
    document.querySelectorAll('.progresso__etapa').forEach((etapa, i) => {
        etapa.dataset.estado = i + 1 === tetoAtual ? 'atual' : leituras[i + 1] ? 'feito' : 'futuro';
    });
    marcarAtivo();
    $('btnCapturar').textContent = rotuloCapturar(tetoAtual);
    vivo.length = 0;   // o gráfico ao vivo recomeça em cada teto
    desenharVivo();
}

function selecionarTeto(n) {
    if (document.body.dataset.fase !== 'medir' || capturando || n === tetoAtual) return;
    tetoAtual = n;
    limparBanner($('avisoMedir'));
    mostrarPasso();
}

// Brinco vazio: o campo fica em erro (borda vermelha e "!") com a explicação por baixo
function erroVaca(sim) {
    $('inputVaca').setAttribute('aria-invalid', String(sim));
    $('erroVaca').hidden = !sim;
}

function iniciar() {
    vaca = normalizarBrinco($('inputVaca').value);
    if (vaca === '') {
        erroVaca(true);
        $('inputVaca').focus();
        vibrar([40, 40, 40]);
        return;
    }
    erroVaca(false);
    limparBanner($('avisoMedir'));
    leituras = {};
    document.querySelectorAll('.teto').forEach(t => {
        mudarEstado(t, 'nao-medido');
        t.querySelector('small').textContent = '';
    });
    tetoAtual = 1;
    $('vacaAtual').textContent = 'Vaca: ' + vaca;
    mostrarFase('medir');
    mostrarPasso();
    iniciarAoVivo();
}

async function capturar() {
    const n = tetoAtual;   // não muda a meio: selecionarTeto espera pelo fim da captura
    const btn = $('btnCapturar');
    capturando = true;
    carregando(btn, true, 'Capturando…');
    const teto = elTeto(n);
    const anterior = leituras[n];   // ao refazer um teto, se falhar fica a leitura que já tinha
    mudarEstado(teto, 'a-ler');

    try {
        const d = await lerSensor();
        if (d.cond < LEITURA_MINIMA) {
            throw new Error('Leitura ' + d.cond + ': a sonda parece estar fora do leite. Repita o teto ' + n + '.');
        }
        leituras[n] = { temp: d.temp, cond: d.cond };
        // Por agora fica "capturado" (verde, com uma onda); o diagnóstico final corrige a cor
        mudarEstado(teto, 'sadio');
        teto.classList.add('capturado');
        teto.querySelector('small').textContent = (temTemp(d) ? d.temp.toFixed(1) + '° / ' : '') + d.cond;
        limparBanner($('avisoMedir'));
        vibrar(30);
    } catch (e) {
        mudarEstado(teto, anterior ? 'sadio' : 'nao-medido');
        banner($('avisoMedir'), 'alerta', e.message);
        vibrar([60, 40, 60]);
        capturando = false;
        carregando(btn, false, rotuloCapturar(n));
        return;
    }

    capturando = false;
    carregando(btn, false, rotuloCapturar(n));

    // Passa ao próximo teto que ainda falta (a seguir a este, dando a volta); se não falta nenhum, grava
    const proximo = [1, 2, 3].map(k => (n - 1 + k) % 4 + 1).find(m => !leituras[m]);
    if (proximo) {
        tetoAtual = proximo;
        mostrarPasso();
    } else {
        tetoAtual = 0;
        marcarAtivo();
        pararAoVivo();
        finalizar();
    }
}

// ---------- Diagnóstico e gravação (feitos pelo servidor) ----------
async function finalizar() {
    const diag = $('diagnostico');
    const estado = $('estadoGravacao');
    mostrarFase('resultado');
    banner(diag, 'analisando', 'A analisar...');
    estado.replaceChildren();

    try {
        const r = await fetch('/api/testes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                brinco: vaca,
                leituras: [1, 2, 3, 4].map(n => ({
                    teto: n, temp: leituras[n].temp, cond: leituras[n].cond
                }))
            })
        });
        const corpo = await r.json();
        if (!r.ok) throw new Error(corpo.erro || ('HTTP ' + r.status));
        mostrarResultado(corpo.teste);
        estado.replaceChildren(
            icone('ic--check'),
            criar('span', null, 'Teste #' + corpo.teste.id + ' guardado no histórico.')
        );
    } catch (e) {
        banner(diag, 'alerta', 'Não foi possível analisar/guardar: ' + e.message);
        // Sem diagnóstico nenhum teto pode ficar verde ("Sadio"): voltam a cinzento, com a leitura
        document.querySelectorAll('.teto').forEach(t => mudarEstado(t, 'nao-medido'));
    }
    carregarHistorico();
}

function mostrarResultado(teste) {
    teste.leituras.forEach(l => {
        const el = elTeto(l.teto);
        mudarEstado(el, l.suspeito ? 'mastite' : 'sadio');
        el.title = l.motivo || '';
        revelar(el, 'revelar', l.teto - 1);   // viram-se um a um, pela ordem de medição
    });

    const diag = $('diagnostico');
    if (teste.tem_mastite) {
        const motivos = teste.leituras
            .filter(l => l.suspeito)
            .map(l => 'Teto ' + l.teto + ': ' + l.motivo);
        banner(diag, 'alerta',
               'ALERTA: suspeita de mastite no(s) teto(s) ' + teste.tetos_afetados.join(', '),
               motivos);
        vibrar([90, 60, 90]);
    } else {
        banner(diag, 'ok', 'Todos os tetos normais.');
        vibrar(40);
    }
}


function novaVaca() {
    $('inputVaca').value = '';
    document.querySelectorAll('.teto').forEach(t => {
        mudarEstado(t, 'nao-medido');
        t.querySelector('small').textContent = '';
        t.classList.remove('ativo', 'revelar');
        t.title = '';
    });
    limparBanner($('diagnostico'));
    limparBanner($('avisoMedir'));
    erroVaca(false);
    mostrarFase('vaca');
    $('inputVaca').focus();
}

// ---------- Histórico e estatísticas (vêm da API) ----------
async function carregarHistorico() {
    const lista = $('listaHistorico');
    try {
        const dados = await (await fetch('/api/testes?limite=10')).json();
        lista.replaceChildren(...dados.testes.map(t => {
            const li = criar('li');
            li.append(itemHistorico(t, true));
            return li;
        }));
        primeiraEntrada(lista);
        filtrarHistorico();   // a procura que já estiver escrita continua a valer
    } catch (e) {
        const aviso = criar('li');
        banner(aviso, 'alerta', 'Erro ao carregar o histórico');
        lista.replaceChildren(aviso);
    }
    carregarEstatisticas();
    carregarVacas();
}

// Sugestões do campo do brinco: as vacas já registadas, com quantos testes têm
async function carregarVacas() {
    try {
        const vacas = await (await fetch('/api/vacas')).json();
        $('listaVacas').replaceChildren(...vacas.map(v => {
            const opcao = criar('option', null, v.testes + (v.testes === 1 ? ' teste' : ' testes'));
            opcao.value = v.brinco;
            return opcao;
        }));
    } catch (e) {
        // sem sugestões o campo continua a aceitar qualquer brinco
    }
}

async function carregarEstatisticas() {
    const caixa = $('estatisticas');
    try {
        const s = await (await fetch('/api/estatisticas')).json();
        caixa.classList.remove('escondido');
        // Contam do valor anterior: depois de um teste novo, "87" passa a "88" sem voltar a zero
        contar($('estVacas'), s.vacas);
        contar($('estTestes'), s.testes);
        contar($('estSuspeita'), s.testes_com_suspeita);
        contar($('estPercentual'), s.percentual_suspeita, v => v + '%');
    } catch (e) {
        caixa.classList.add('escondido');
    }
}

// ---------- Procurar uma vaca no histórico ----------
// Escrever filtra os últimos testes; enviar (Enter ou a seta) abre o histórico completo dela
function filtrarHistorico() {
    const termo = normalizarBrinco($('inputProcura').value);
    let visiveis = 0;
    document.querySelectorAll('#listaHistorico > li').forEach(li => {
        const brinco = li.querySelector('.item__vaca');
        li.hidden = Boolean(termo && brinco && !brinco.textContent.includes(termo));
        if (!li.hidden) visiveis++;
    });
    $('procuraVazia').hidden = !termo || visiveis > 0;
}

function abrirVaca(e) {
    e.preventDefault();
    const brinco = normalizarBrinco($('inputProcura').value);
    if (brinco === '') {
        $('inputProcura').focus();
        return;
    }
    location.href = '/vacas/' + encodeURIComponent(brinco);
}

// ---------- Ligações ----------
$('btnIniciar').addEventListener('click', iniciar);
$('btnCapturar').addEventListener('click', capturar);
document.querySelectorAll('.teto').forEach(t => {
    const escolher = () => selecionarTeto(Number(t.dataset.teto));
    t.addEventListener('click', escolher);
    t.addEventListener('keydown', e => {   // o teto só é focável enquanto se mede (mostrarFase)
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            escolher();
        }
    });
});
$('btnNova').addEventListener('click', novaVaca);
$('inputVaca').addEventListener('input', () => erroVaca(false));
$('inputProcura').addEventListener('input', filtrarHistorico);
$('procurarVaca').addEventListener('submit', abrirVaca);
carregarHistorico();
