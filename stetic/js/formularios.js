// Formulários de entrada, conta e verificação em dois passos:
// mostrar/ocultar a senha, botão "a enviar" e copiar a chave do MFA.
// Dentro de { }: os nomes não chocam com os dos outros scripts da página (login.js).
{
    // Mostrar a senha: um botão dentro do campo. O rótulo não muda; aria-pressed diz o estado.
    document.querySelectorAll('.campo[type="password"]').forEach(campo => {
        const caixa = campo.closest('.campo-caixa');
        const botao = document.createElement('button');
        botao.type = 'button';
        botao.className = 'campo__olho';
        botao.setAttribute('aria-label', 'Mostrar senha');
        botao.setAttribute('aria-pressed', 'false');
        botao.setAttribute('aria-controls', campo.id);
        botao.addEventListener('click', () => {
            const mostrar = campo.type === 'password';
            campo.type = mostrar ? 'text' : 'password';
            botao.setAttribute('aria-pressed', String(mostrar));
        });
        caixa.classList.add('campo-caixa--senha');
        caixa.append(botao);
    });

    // Ao enviar: o botão mostra que está a trabalhar e um segundo toque não envia outra vez.
    // As senhas voltam a "password" antes de sair, para o gestor de senhas as reconhecer.
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', e => {
            if (form.dataset.aEnviar) {
                e.preventDefault();
                return;
            }
            form.dataset.aEnviar = '1';
            form.querySelectorAll('.campo-caixa--senha .campo').forEach(c => { c.type = 'password'; });
            form.querySelector('.btn[type="submit"]')?.setAttribute('aria-busy', 'true');
        });
    });

    // Voltar atrás pode trazer a página da cache do navegador: o botão não fica preso no "a enviar"
    window.addEventListener('pageshow', e => {
        if (!e.persisted) return;
        document.querySelectorAll('form[data-a-enviar]').forEach(form => {
            delete form.dataset.aEnviar;
            form.querySelector('[aria-busy="true"]')?.removeAttribute('aria-busy');
        });
    });

    // Copiar a chave do MFA (para quem não consegue ler o QR).
    // Em http, na rede da fazenda, o navegador não dá a API da área de transferência: seleciona e usa o comando antigo.
    document.querySelectorAll('[data-copiar]').forEach(botao => {
        const alvo = document.getElementById(botao.dataset.copiar);
        const rotulo = botao.textContent;
        botao.addEventListener('click', async () => {
            const texto = alvo.textContent.trim();
            let copiou = false;
            try {
                await navigator.clipboard.writeText(texto);
                copiou = true;
            } catch (e) {
                const intervalo = document.createRange();
                intervalo.selectNodeContents(alvo);
                getSelection().removeAllRanges();
                getSelection().addRange(intervalo);
                copiou = document.execCommand('copy');
            }
            botao.textContent = copiou ? 'Chave copiada' : 'Chave selecionada: copie-a';
            setTimeout(() => { botao.textContent = rotulo; }, 2500);
        });
    });
}
