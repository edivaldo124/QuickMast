// Painel de estatísticas: só lê GET /api/estatisticas.
const $ = id => document.getElementById(id);

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

carregar();
