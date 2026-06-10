import { showScreen } from './app.js';

let infracoes = [];
let filtroGravidade = 'todas';

const GRAVIDADE_CONFIG = {
    gravissima: { label: 'Gravíssima', classe: 'gravissima' },
    grave:      { label: 'Grave',      classe: 'grave' },
    media:      { label: 'Média',      classe: 'media' },
    leve:       { label: 'Leve',       classe: 'leve' },
};

const ORDEM_GRAVIDADE = ['gravissima', 'grave', 'media', 'leve'];

export async function initInfracoes() {
    if (!infracoes.length) {
        const res = await fetch('data/infracoes.json');
        infracoes = await res.json();
    }

    filtroGravidade = 'todas';
    renderInfracoes('');

    const searchEl = document.getElementById('infracoes-search');
    searchEl.value = '';
    searchEl.replaceWith(searchEl.cloneNode(true));
    document.getElementById('infracoes-search').addEventListener('input', e => {
        renderInfracoes(e.target.value.trim().toLowerCase());
    });

    document.querySelectorAll('.filtro-btn').forEach(btn => {
        btn.replaceWith(btn.cloneNode(true));
    });
    document.querySelectorAll('.filtro-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            filtroGravidade = btn.dataset.gravidade;
            document.querySelectorAll('.filtro-btn').forEach(b => b.classList.remove('filtro-ativo'));
            btn.classList.add('filtro-ativo');
            const busca = document.getElementById('infracoes-search').value.trim().toLowerCase();
            renderInfracoes(busca);
        });
    });

    showScreen('infracoes');
}

function formatarValor(valor) {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function aplicarFiltros(busca) {
    return infracoes.filter(inf => {
        const passaGravidade = filtroGravidade === 'todas' || inf.gravidade === filtroGravidade;
        const passaBusca = !busca ||
            inf.descricao.toLowerCase().includes(busca) ||
            inf.artigo.toLowerCase().includes(busca);
        return passaGravidade && passaBusca;
    });
}

function renderInfracoes(busca) {
    const container = document.getElementById('infracoes-container');
    container.innerHTML = '';
    const lista = aplicarFiltros(busca);

    if (!lista.length) {
        document.getElementById('infracoes-count').textContent = 'Nenhuma infração encontrada';
        return;
    }

    if (busca || filtroGravidade !== 'todas') {
        document.getElementById('infracoes-count').textContent = `${lista.length} infração(ões)`;
        container.appendChild(buildGrupo(lista));
        return;
    }

    let total = 0;
    ORDEM_GRAVIDADE.forEach(grav => {
        const grupo = lista.filter(inf => inf.gravidade === grav);
        if (!grupo.length) return;

        const config = GRAVIDADE_CONFIG[grav];
        const section = document.createElement('div');
        section.className = 'infracoes-section';

        const header = document.createElement('div');
        header.className = `infracoes-section-header infracoes-header-${config.classe}`;
        header.innerHTML = `<h3>${config.label}</h3><span class="infracoes-section-count">${grupo.length} infração(ões)</span>`;
        section.appendChild(header);
        section.appendChild(buildGrupo(grupo));
        container.appendChild(section);
        total += grupo.length;
    });

    document.getElementById('infracoes-count').textContent = `${total} infração(ões)`;
}

function buildGrupo(lista) {
    const grid = document.createElement('div');
    grid.className = 'infracoes-grid';
    lista.forEach(inf => {
        const config = GRAVIDADE_CONFIG[inf.gravidade];
        const card = document.createElement('div');
        card.className = `infracao-card infracao-${config.classe}`;
        card.innerHTML = `
            <div class="infracao-header">
                <span class="infracao-badge infracao-badge-${config.classe}">${config.label}</span>
                <span class="infracao-artigo">Art. ${inf.artigo}</span>
            </div>
            <p class="infracao-descricao">${inf.descricao}</p>
            ${inf.observacao ? `<p class="infracao-obs">${inf.observacao}</p>` : ''}
            <div class="infracao-footer">
                <span class="infracao-valor">${formatarValor(inf.valor)}</span>
                <span class="infracao-pontos">${inf.pontos} ponto${inf.pontos !== 1 ? 's' : ''}</span>
            </div>
        `;
        grid.appendChild(card);
    });
    return grid;
}
