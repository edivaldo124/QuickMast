// Painel de estatísticas: só lê GET /api/estatisticas.
const $ = id => document.getElementById(id);

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

async function carregar() {
    try {
        const r = await fetch('/api/estatisticas');
        const s = await r.json();
        if (!r.ok) throw new Error(s.erro);

        $('tempMedia').textContent = s.temp_media === null ? '--' : s.temp_media.toFixed(1) + ' °C';
        $('condMedia').textContent = s.cond_media === null ? '--' : s.cond_media;

        // Intensidade relativa ao teto com mais suspeitas
        const max = Math.max(...Object.values(s.suspeitas_por_teto));
        document.querySelectorAll('.mapa__teto').forEach(el => {
            const n = s.suspeitas_por_teto[el.dataset.teto];
            const alfa = 0.12 + (max ? n / max : 0) * 0.88;
            el.style.setProperty('--alfa', alfa.toFixed(2));
            el.style.setProperty('--cor-texto', corTexto(alfa));
            el.querySelector('.mapa__numero').textContent = n;
        });
        $('escalaMax').textContent = max;
    } catch (e) {
        banner($('mensagem'), 'alerta', 'Erro ao carregar as estatísticas');
    }
}

carregar();
