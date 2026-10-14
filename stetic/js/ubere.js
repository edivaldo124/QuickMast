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
let leituras = {};          // {1: {temp, cond}, 2: ...}
let lendoAoVivo = false;    // evita pedidos /read sobrepostos
let timerVivo = null;

// ---------- Elementos da página ----------
const $ = id => document.getElementById(id);

function elTeto(n) {
    return document.querySelector('.teto[data-teto="' + n + '"]');
}

function mudarEstado(teto, estado) {
    teto.classList.remove('nao-medido', 'a-ler', 'sadio', 'mastite');
    teto.classList.add(estado);
    teto.querySelector('.teto__estado').textContent = ESTADOS[estado];
}

// Mostra só os blocos da fase: 'vaca', 'medir' ou 'resultado' (ver data-fases no HTML)
function mostrarFase(fase) {
    document.body.dataset.fase = fase;
}

// Botão grande no estado "Carregando" (spinner + texto) ou de volta ao normal
function carregando(btn, sim, rotulo) {
    btn.disabled = sim;
    btn.setAttribute('aria-busy', String(sim));
    btn.textContent = rotulo;
}

// ---------- Leitura em tempo real (a cada 2 s) ----------
async function lerAoVivo() {
    if (lendoAoVivo || tetoAtual === 0) return;
    lendoAoVivo = true;
    try {
        const d = await (await fetch('/read')).json();
        $('vivoTemp').textContent = d.temp.toFixed(1);
        $('vivoCond').textContent = d.cond;
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

// ---------- Wizard ----------
function mostrarPasso() {
    $('instrucao').textContent =
        'Insira a sonda no Teto ' + tetoAtual + ' (' + NOMES[tetoAtual] + ')';
    $('progressoTexto').textContent = tetoAtual + ' de 4';
    document.querySelectorAll('.progresso__etapa').forEach((etapa, i) => {
        etapa.dataset.estado = i + 1 < tetoAtual ? 'feito' : i + 1 === tetoAtual ? 'atual' : 'futuro';
    });
    document.querySelectorAll('.teto').forEach(t => t.classList.remove('ativo'));
    elTeto(tetoAtual).classList.add('ativo');
}

function iniciar() {
    vaca = $('inputVaca').value.trim();
    if (vaca === '') {
        alert('Escreva o brinco/ID da vaca.');
        return;
    }
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
    const btn = $('btnCapturar');
    carregando(btn, true, 'Capturando…');
    const teto = elTeto(tetoAtual);
    mudarEstado(teto, 'a-ler');

    try {
        const d = await (await fetch('/read')).json();
        leituras[tetoAtual] = { temp: d.temp, cond: d.cond };
        // Por agora fica "capturado" (verde); o diagnóstico final corrige a cor
        mudarEstado(teto, 'sadio');
        teto.querySelector('small').textContent = d.temp.toFixed(1) + '° / ' + d.cond;
    } catch (e) {
        mudarEstado(teto, 'nao-medido');
        alert('Erro de comunicação com o servidor/placa.');
        carregando(btn, false, 'Capturar amostra');
        return;
    }

    carregando(btn, false, 'Capturar amostra');
    teto.classList.remove('ativo');

    if (tetoAtual < 4) {
        tetoAtual++;
        mostrarPasso();
    } else {
        tetoAtual = 0;
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
    });

    const diag = $('diagnostico');
    if (teste.tem_mastite) {
        const motivos = teste.leituras
            .filter(l => l.suspeito)
            .map(l => 'Teto ' + l.teto + ': ' + l.motivo);
        banner(diag, 'alerta',
               'ALERTA: suspeita de mastite no(s) teto(s) ' + teste.tetos_afetados.join(', '),
               motivos);
    } else {
        banner(diag, 'ok', 'Todos os tetos normais.');
    }
}


function novaVaca() {
    $('inputVaca').value = '';
    document.querySelectorAll('.teto').forEach(t => {
        mudarEstado(t, 'nao-medido');
        t.querySelector('small').textContent = '';
        t.classList.remove('ativo');
        t.title = '';
    });
    limparBanner($('diagnostico'));
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
    } catch (e) {
        const aviso = criar('li');
        banner(aviso, 'alerta', 'Erro ao carregar o histórico');
        lista.replaceChildren(aviso);
    }
    carregarEstatisticas();
}

async function carregarEstatisticas() {
    const caixa = $('estatisticas');
    try {
        const s = await (await fetch('/api/estatisticas')).json();
        $('estVacas').textContent = s.vacas;
        $('estTestes').textContent = s.testes;
        $('estSuspeita').textContent = s.testes_com_suspeita;
        $('estPercentual').textContent = s.percentual_suspeita + '%';
        caixa.classList.remove('escondido');
    } catch (e) {
        caixa.classList.add('escondido');
    }
}

// ---------- Ligações ----------
$('btnIniciar').addEventListener('click', iniciar);
$('btnCapturar').addEventListener('click', capturar);
$('btnNova').addEventListener('click', novaVaca);
carregarHistorico();
