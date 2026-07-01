import { showScreen } from './app.js';

let provaState = null;
let timerInterval = null;
let estudoState = null;

const PROVA_COUNT = 30;
const PROVA_SECONDS = 40 * 60;

function shuffle(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}

export function cancelProva() {
    clearInterval(timerInterval);
    provaState = null;
}

export function startProva(questoes) {
    provaState = {
        questions: shuffle(questoes).slice(0, PROVA_COUNT),
        current: 0,
        answers: {},
    };
    renderProvaQuestion();
    startTimer(PROVA_SECONDS, updateTimerDisplay, finalizarProva);
    showScreen('prova');
}

function renderProvaQuestion() {
    const q = provaState.questions[provaState.current];
    const total = provaState.questions.length;

    document.getElementById('prova-progress').textContent =
        `Questão ${provaState.current + 1} / ${total}`;
    document.getElementById('prova-enunciado').textContent = q.enunciado;

    const placaEl = document.getElementById('prova-placa');
    if (q.imagem_placa) {
        placaEl.src = q.imagem_placa;
        placaEl.hidden = false;
    } else {
        placaEl.hidden = true;
    }

    const altsEl = document.getElementById('prova-alternativas');
    altsEl.innerHTML = '';
    ['A', 'B', 'C', 'D'].forEach(letra => {
        if (!q.alternativas[letra]) return;
        const btn = document.createElement('button');
        btn.className = 'btn-alt';
        btn.dataset.letra = letra;
        btn.textContent = `${letra}) ${q.alternativas[letra]}`;
        const chosen = provaState.answers[q.id];
        if (chosen === letra) btn.classList.add('selected');
        btn.addEventListener('click', () => escolherAlt(q.id, letra));
        altsEl.appendChild(btn);
    });

    document.getElementById('btn-prova-anterior').disabled = provaState.current === 0;
    document.getElementById('btn-prova-proximo').textContent =
        provaState.current === total - 1 ? 'Finalizar' : 'Próxima →';
}

function escolherAlt(qId, letra) {
    provaState.answers[qId] = letra;
    renderProvaQuestion();
}

function startTimer(seconds, onTick, onExpire) {
    const end = Date.now() + seconds * 1000;
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        const rem = Math.ceil((end - Date.now()) / 1000);
        if (rem <= 0) {
            clearInterval(timerInterval);
            onExpire();
        } else {
            onTick(rem);
        }
    }, 500);
}

function updateTimerDisplay(remaining) {
    const m = String(Math.floor(remaining / 60)).padStart(2, '0');
    const s = String(remaining % 60).padStart(2, '0');
    const el = document.getElementById('prova-timer');
    el.textContent = `${m}:${s}`;
    if (remaining <= 300) {
        el.classList.add('timer-urgent');
    }
}

function finalizarProva() {
    clearInterval(timerInterval);
    renderResultado(provaState);
    showScreen('resultado');
}

function renderResultado(state) {
    const { questions, answers } = state;
    let acertos = 0;

    questions.forEach(q => {
        if (answers[q.id] === q.gabarito) acertos++;
    });

    const aprovado = acertos >= 21;
    document.getElementById('resultado-placar').textContent = `${acertos} / 30`;
    document.getElementById('resultado-status').textContent = aprovado ? 'APROVADO' : 'REPROVADO';
    document.getElementById('resultado-status').className = aprovado ? 'approved' : 'failed';

    const listEl = document.getElementById('resultado-lista');
    listEl.innerHTML = '';
    questions.forEach((q, i) => {
        const chosen = answers[q.id];
        const correct = chosen === q.gabarito;
        const div = document.createElement('div');
        div.className = `resultado-item ${correct ? 'correct' : 'wrong'}`;

        const altsHtml = ['A', 'B', 'C', 'D']
            .filter(l => q.alternativas[l])
            .map(l => {
                let cls = 'resultado-alt';
                if (l === q.gabarito) cls += ' resultado-alt-correct';
                else if (l === chosen) cls += ' resultado-alt-wrong';
                return `<div class="${cls}"><strong>${l})</strong> ${q.alternativas[l]}</div>`;
            }).join('');

        div.innerHTML = `
            <p><strong>${i + 1}.</strong> ${q.enunciado}</p>
            ${q.imagem_placa ? `<img src="${q.imagem_placa}" class="placa-sm" alt="${q.codigo_placa}" onerror="this.style.display='none'">` : ''}
            <div class="resultado-alts">${altsHtml}</div>
            ${q.explicacao ? `<p class="explicacao">${q.explicacao}</p>` : ''}
        `;
        listEl.appendChild(div);
    });
}

const MODULO_NAMES = {
    1: 'Placas, Cores e Caminhos',
    2: 'Escolhas e Consequências',
    3: 'Na Direção da Segurança',
    4: 'Cuidar, Agir e Preservar',
    5: 'DETRAN SP',
};

let estudoQuestoes = [];

export function initEstudoConfig(questoes) {
    estudoQuestoes = questoes;
    const modulos = [...new Set(questoes.map(q => q.modulo))].sort((a, b) => a - b);
    const container = document.getElementById('estudo-modulos');
    container.innerHTML = '';
    modulos.forEach(n => {
        const label = document.createElement('label');
        label.innerHTML = `<input type="checkbox" value="${n}" checked> Módulo ${n} — ${MODULO_NAMES[n] ?? n}`;
        container.appendChild(label);
    });

    document.getElementById('btn-iniciar-estudo').onclick = () => {
        const checked = [...container.querySelectorAll('input:checked')].map(i => +i.value);
        if (!checked.length) return;
        startEstudo(estudoQuestoes, checked);
    };
}

function startEstudo(questoes, modulos) {
    const pool = questoes.filter(q => modulos.includes(q.modulo));
    estudoState = {
        questions: shuffle(pool),
        current: 0,
        acertos: 0,
        erros: 0,
        answered: false,
    };
    renderEstudoQuestion();
    showScreen('estudo-questao');
}

function renderEstudoQuestion() {
    const { questions, current } = estudoState;
    const q = questions[current];
    estudoState.answered = false;

    document.getElementById('estudo-progress').textContent =
        `${current + 1} / ${questions.length}`;
    document.getElementById('estudo-enunciado').textContent = q.enunciado;

    const placaEl = document.getElementById('estudo-placa');
    placaEl.onload = null;
    placaEl.onerror = null;
    placaEl.hidden = true;
    if (q.imagem_placa) {
        placaEl.onload = () => { placaEl.hidden = false; };
        placaEl.onerror = () => { placaEl.hidden = true; };
        placaEl.src = q.imagem_placa;
    }

    const altsEl = document.getElementById('estudo-alternativas');
    altsEl.innerHTML = '';
    ['A', 'B', 'C', 'D'].forEach(letra => {
        if (!q.alternativas[letra]) return;
        const btn = document.createElement('button');
        btn.className = 'btn-alt';
        btn.dataset.letra = letra;
        btn.textContent = `${letra}) ${q.alternativas[letra]}`;
        btn.addEventListener('click', () => responderEstudo(q, letra));
        altsEl.appendChild(btn);
    });

    document.getElementById('estudo-feedback').hidden = true;
    document.getElementById('btn-estudo-proximo').hidden = true;
}

function responderEstudo(q, letra) {
    if (estudoState.answered) return;
    estudoState.answered = true;

    const acertou = letra === q.gabarito;
    if (acertou) estudoState.acertos++; else estudoState.erros++;

    document.querySelectorAll('#estudo-alternativas .btn-alt').forEach(btn => {
        btn.disabled = true;
        if (btn.dataset.letra === q.gabarito) btn.classList.add('correct');
        else if (btn.dataset.letra === letra) btn.classList.add('wrong');
    });

    const feedback = document.getElementById('estudo-feedback');
    const iconEl = document.getElementById('estudo-feedback-icon');
    iconEl.textContent = acertou ? '✓' : '✗';
    iconEl.className = acertou ? 'correct' : 'wrong';
    document.getElementById('estudo-explicacao').textContent = q.explicacao;
    feedback.hidden = false;

    document.getElementById('btn-estudo-proximo').hidden = false;
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btn-prova-anterior')?.addEventListener('click', () => {
        if (provaState && provaState.current > 0) {
            provaState.current--;
            renderProvaQuestion();
        }
    });

    document.getElementById('btn-prova-proximo')?.addEventListener('click', () => {
        if (!provaState) return;
        if (provaState.current === provaState.questions.length - 1) {
            finalizarProva();
        } else {
            provaState.current++;
            renderProvaQuestion();
        }
    });

    document.getElementById('btn-estudo-proximo')?.addEventListener('click', () => {
        if (!estudoState) return;
        document.getElementById('btn-estudo-proximo').hidden = true;
        estudoState.current++;
        if (estudoState.current >= estudoState.questions.length) {
            showScreen('home');
        } else {
            renderEstudoQuestion();
        }
    });
});
