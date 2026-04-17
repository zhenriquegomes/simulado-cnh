import { showScreen } from './app.js';

let catalog = [];
let flatPlates = [];

export async function initPlacas() {
    if (!catalog.length) {
        const res = await fetch('data/placas_catalog.json');
        catalog = await res.json();
        flatPlates = catalog.flatMap(s => s.plates.map(p => ({ ...p, series: s.name })));
    }

    renderGallery('');
    const searchEl = document.getElementById('placas-search');
    searchEl.value = '';
    searchEl.replaceWith(searchEl.cloneNode(true));
    document.getElementById('placas-search').addEventListener('input', e => {
        renderGallery(e.target.value.trim().toLowerCase());
    });
    showScreen('placas');
}

function renderGallery(filtro) {
    const container = document.getElementById('placas-grid');
    container.innerHTML = '';

    if (filtro) {
        const matches = flatPlates.filter(p =>
            p.code.toLowerCase().includes(filtro) ||
            p.description.toLowerCase().includes(filtro)
        );
        document.getElementById('placas-count').textContent = `${matches.length} placa(s)`;
        container.appendChild(buildGrid(matches));
        return;
    }

    let total = 0;
    catalog.forEach(series => {
        const section = document.createElement('div');
        section.className = 'placas-section';

        const header = document.createElement('div');
        header.className = 'placas-section-header';
        header.innerHTML = `<h3>${series.name}</h3><p>${series.description}</p>`;
        section.appendChild(header);
        section.appendChild(buildGrid(series.plates));
        container.appendChild(section);
        total += series.plates.length;
    });

    document.getElementById('placas-count').textContent = `${total} placa(s)`;
}

function buildGrid(plates) {
    const grid = document.createElement('div');
    grid.className = 'placas-grid';
    plates.forEach(p => {
        const card = document.createElement('div');
        card.className = 'placa-card';
        card.innerHTML = `
            <img src="${p.image}" alt="${p.code}" loading="lazy" onerror="this.style.display='none'">
            <span class="placa-code">${p.code}</span>
            <span class="placa-desc">${p.description}</span>
        `;
        grid.appendChild(card);
    });
    return grid;
}
