import json
import urllib.request
import urllib.parse
import time
from pathlib import Path

GITHUB_RAW = 'https://raw.githubusercontent.com/sergio-ishii-pinhais/Brazil-PlacasDeTransito-SVG/main/Brasil_{}.svg'
COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
OUT_DIR = Path(__file__).parent.parent / 'assets' / 'placas'
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {'User-Agent': 'simulado-cnh/1.0 (educational project)'}


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def try_github(codigo):
    url = GITHUB_RAW.format(codigo)
    try:
        content = fetch(url)
        if b'<svg' in content:
            return content
    except Exception:
        pass
    return None


def try_wikimedia(codigo):
    params = urllib.parse.urlencode({
        'action': 'query',
        'titles': f'File:Brasil_{codigo}.svg',
        'prop': 'imageinfo',
        'iiprop': 'url',
        'format': 'json',
    })
    try:
        data = json.loads(fetch(f'{COMMONS_API}?{params}', timeout=10))
        pages = data['query']['pages']
        page = next(iter(pages.values()))
        if 'imageinfo' not in page:
            return None
        img_url = page['imageinfo'][0]['url']
        time.sleep(2)
        content = fetch(img_url)
        if b'<svg' in content:
            return content
    except Exception:
        pass
    return None


def make_placeholder(codigo):
    color = '#e63946' if codigo.startswith('R') else '#f4a261' if codigo.startswith('A') else '#457b9d'
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <rect width="100" height="100" rx="8" fill="{color}"/>
  <text x="50" y="55" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="bold" fill="white">{codigo}</text>
</svg>'''
    return svg.encode()


def download(codigo):
    out = OUT_DIR / f'{codigo}.svg'
    if out.exists():
        print(f'  skip  {codigo}')
        return 'skip'

    content = try_github(codigo)
    if content:
        out.write_bytes(content)
        print(f'  github {codigo} ({len(content)}b)')
        return 'github'

    time.sleep(1)
    content = try_wikimedia(codigo)
    if content:
        out.write_bytes(content)
        print(f'  wiki   {codigo} ({len(content)}b)')
        return 'wiki'

    content = make_placeholder(codigo)
    out.write_bytes(content)
    print(f'  placeholder {codigo}')
    return 'placeholder'


if __name__ == '__main__':
    data = json.load(open(Path(__file__).parent.parent / 'data' / 'questoes.json'))
    codigos = sorted(set(q['codigo_placa'] for q in data if q['codigo_placa']))
    print(f'Baixando {len(codigos)} placas...\n')

    counts = {'skip': 0, 'github': 0, 'wiki': 0, 'placeholder': 0}
    for codigo in codigos:
        result = download(codigo)
        counts[result] += 1
        time.sleep(0.5)

    total = sum(counts.values())
    print(f'\nTotal: {total} | GitHub: {counts["github"]} | Wiki: {counts["wiki"]} | Placeholder: {counts["placeholder"]} | Skip: {counts["skip"]}')
