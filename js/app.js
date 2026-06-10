import { startProva, cancelProva } from './quiz.js';
import { initEstudoConfig } from './quiz.js';
import { initPlacas } from './placas.js';
import { initInfracoes } from './infracoes.js';

export let questoes = [];

const SCREENS = ['home', 'prova', 'resultado', 'estudo-config', 'estudo-questao', 'placas', 'infracoes'];

const SCREEN_TITLES = {
    'prova':          'Modo Prova',
    'resultado':      'Resultado',
    'estudo-config':  'Modo Estudo',
    'estudo-questao': 'Modo Estudo',
    'placas':         'Galeria de Placas',
    'infracoes':      'Infrações de Trânsito',
};

export function showScreen(name) {
    SCREENS.forEach(s => {
        document.getElementById(`screen-${s}`).hidden = (s !== name);
    });
    const isHome = name === 'home';
    document.getElementById('global-header').hidden = isHome;
    document.getElementById('header-title').textContent = SCREEN_TITLES[name] ?? '';
}

async function init() {
    try {
        const res = await fetch('data/questoes.json');
        if (!res.ok) throw new Error(res.statusText);
        questoes = await res.json();
    } catch (e) {
        document.getElementById('error-msg').hidden = false;
        return;
    }

    document.getElementById('btn-prova').addEventListener('click', () => startProva(questoes));
    document.getElementById('btn-estudo').addEventListener('click', () => showScreen('estudo-config'));
    document.getElementById('btn-placas').addEventListener('click', () => initPlacas());
    document.getElementById('btn-infracoes').addEventListener('click', () => initInfracoes());

    document.getElementById('btn-back-home').addEventListener('click', () => {
        cancelProva();
        showScreen('home');
    });

    initEstudoConfig(questoes);
    showScreen('home');
}

document.addEventListener('DOMContentLoaded', init);
