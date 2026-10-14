// Alterna entre "Entrar" e "Criar conta"
const formEntrar = document.getElementById('formEntrar');
const formCriar = document.getElementById('formCriar');

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

