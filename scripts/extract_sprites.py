"""
Baixa sprites do placasdetransito.com.br e extrai SVGs individuais por id.
"""
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

OUT_DIR = Path(__file__).parent.parent / 'assets' / 'placas'
HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}

SPRITES = {
    'advertencia':       'https://www.placasdetransito.com.br/assets/images/advertencia.svg',
    'regulamentacao':    'https://www.placasdetransito.com.br/assets/images/regulamentacao.svg',
    'servicos':          'https://www.placasdetransito.com.br/assets/images/servicos_auxiliares.svg',
    'turisticos':        'https://www.placasdetransito.com.br/assets/images/atrativos_turisticos.svg',
}

TARGETS = {
    'A-41':   'advertencia',
    'R-35':   'regulamentacao',
    'SAU-06': 'servicos',
    'SAU-08': 'servicos',
    'SAU-09': 'servicos',
    'SAU-10': 'servicos',
    'SAU-12': 'servicos',
    'SAU-13': 'servicos',
    'SAU-18': 'servicos',
    'SAU-21': 'servicos',
    'SAU-26': 'servicos',
    'TAR-03': 'turisticos',
    'THC-05': 'turisticos',
    'THC-11': 'turisticos',
    'TNA-05': 'turisticos',
    'TNA-06': 'turisticos',
}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def extract_symbol(svg_text, symbol_id):
    """Extract a <symbol id="X"> and return standalone SVG."""
    root = ET.fromstring(svg_text)
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

    # Try <symbol id="...">
    for sym in root.iter('{http://www.w3.org/2000/svg}symbol'):
        if sym.get('id') == symbol_id:
            vb = sym.get('viewBox', '0 0 100 100')
            inner = ET.tostring(sym, encoding='unicode')
            inner = re.sub(r'^<symbol[^>]*>', '', inner)
            inner = re.sub(r'</symbol>$', '', inner)
            return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="{vb}">{inner}</svg>'

    # Try <g id="...">
    for g in root.iter('{http://www.w3.org/2000/svg}g'):
        if g.get('id') == symbol_id:
            vb = root.get('viewBox', '0 0 100 100')
            inner = ET.tostring(g, encoding='unicode')
            return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="{vb}">{inner}</svg>'

    return None


def main():
    sprites_cache = {}

    for codigo, sprite_key in TARGETS.items():
        out = OUT_DIR / f'{codigo}.svg'
        if out.exists() and out.stat().st_size > 500:
            print(f'  skip  {codigo}')
            continue

        if sprite_key not in sprites_cache:
            print(f'  fetch sprite: {sprite_key}')
            sprites_cache[sprite_key] = fetch(SPRITES[sprite_key])

        svg = extract_symbol(sprites_cache[sprite_key], codigo)
        if svg:
            out.write_text(svg, encoding='utf-8')
            print(f'  OK    {codigo} ({len(svg)}b)')
        else:
            # try listing available ids for debug
            text = sprites_cache[sprite_key]
            ids = re.findall(r'id="([^"]+)"', text)
            matches = [i for i in ids if codigo.split('-')[0] in i]
            print(f'  MISS  {codigo} — similar ids: {matches[:10]}')


if __name__ == '__main__':
    main()


