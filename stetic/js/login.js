// Alterna entre "Entrar" e "Criar conta" (o "Criar conta" só existe com o registo público ligado)
const formEntrar = document.getElementById('formEntrar');
const formCriar = document.getElementById('formCriar');

if (formCriar) {
    document.getElementById('irCriar').addEventListener('click', e => {
        e.preventDefault();
        formEntrar.classList.add('escondido');
        formCriar.classList.remove('escondido');
    });
    document.getElementById('irEntrar').addEventListener('click', e => {
        e.preventDefault();
        formCriar.classList.add('escondido');
        formEntrar.classList.remove('escondido');
    });
}

