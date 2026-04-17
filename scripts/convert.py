import re
import json
import sys
from pathlib import Path

RE_PARTE    = re.compile(r'^## PARTE (\d+)')
RE_MODULO   = re.compile(r'^## MÓDULO (\d+) - (.+)')
RE_QUESTAO  = re.compile(r'^### [🟢🟡🔴] Questão (\d+) \((.+?)\)')
RE_ENUNC    = re.compile(r'^\*\*(.+)\*\*$')
RE_PLACA    = re.compile(r'^> Código da placa: (.+)')
RE_ALT      = re.compile(r'^- \*\*(A|B|C|D)\)\*\* (.+)')

RE_GABARITO = re.compile(r'^### Questão (\d+) — Resposta: \*\*([A-D])\)\*\*')
RE_CORRETA  = re.compile(r'^\*\*Correta:\*\* (.+)')
RE_EXPLIC   = re.compile(r'^> (.+)')


def parse_questoes(path):
    questions = {}
    parte = modulo = modulo_nome = None
    current = None

    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')

        m = RE_PARTE.match(line)
        if m:
            parte = int(m.group(1))
            current = None
            continue

        m = RE_MODULO.match(line)
        if m:
            modulo = int(m.group(1))
            modulo_nome = m.group(2).strip()
            current = None
            continue

        m = RE_QUESTAO.match(line)
        if m:
            q_num = int(m.group(1))
            dificuldade = m.group(2)
            current = {
                'parte': parte,
                'modulo': modulo,
                'modulo_nome': modulo_nome,
                'num': q_num,
                'dificuldade': dificuldade,
                'enunciado': None,
                'codigo_placa': None,
                'alternativas': {},
            }
            questions[(parte, modulo, q_num)] = current
            continue

        if current is None:
            continue

        m = RE_ALT.match(line)
        if m:
            current['alternativas'][m.group(1)] = m.group(2).strip()
            continue

        m = RE_PLACA.match(line)
        if m:
            current['codigo_placa'] = m.group(1).strip()
            continue

        m = RE_ENUNC.match(line)
        if m and current['enunciado'] is None and not current['alternativas']:
            current['enunciado'] = m.group(1).strip()
            continue

    return questions


def parse_gabarito(path):
    answers = {}
    parte = modulo = None
    current_key = None
    explic_lines = []

    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')

        m = RE_PARTE.match(line)
        if m:
            if current_key and explic_lines:
                answers[current_key]['explicacao'] = ' '.join(explic_lines)
            parte = int(m.group(1))
            current_key = None
            explic_lines = []
            continue

        m = RE_MODULO.match(line)
        if m:
            if current_key and explic_lines:
                answers[current_key]['explicacao'] = ' '.join(explic_lines)
            modulo = int(m.group(1))
            current_key = None
            explic_lines = []
            continue

        m = RE_GABARITO.match(line)
        if m:
            if current_key and explic_lines:
                answers[current_key]['explicacao'] = ' '.join(explic_lines)
            q_num = int(m.group(1))
            current_key = (parte, modulo, q_num)
            answers[current_key] = {'gabarito': m.group(2), 'explicacao': ''}
            explic_lines = []
            continue

        if current_key is None:
            continue

        m = RE_EXPLIC.match(line)
        if m:
            explic_lines.append(m.group(1).strip())

    if current_key and explic_lines:
        answers[current_key]['explicacao'] = ' '.join(explic_lines)

    return answers


def build_json(questoes, gabarito):
    result = []
    global_id = 1
    modulo_nomes = {
        1: 'Placas, Cores e Caminhos',
        2: 'Escolhas e Consequências',
        3: 'Na Direção da Segurança',
        4: 'Cuidar, Agir e Preservar',
    }
    for key in sorted(questoes):
        q = questoes[key]
        a = gabarito.get(key, {})
        if not a:
            print(f'WARNING: sem gabarito para questão {key}', file=sys.stderr)
        codigo = q['codigo_placa']
        if codigo and ' e ' in codigo:
            codigo = codigo.split(' e ')[0].strip()
        result.append({
            'id': global_id,
            'parte': q['parte'],
            'modulo': q['modulo'],
            'modulo_nome': modulo_nomes.get(q['modulo'], f'Módulo {q["modulo"]}'),
            'dificuldade': q['dificuldade'],
            'enunciado': q['enunciado'],
            'codigo_placa': codigo,
            'imagem_placa': f'assets/placas/{codigo}.svg' if codigo else None,
            'alternativas': q['alternativas'],
            'gabarito': a.get('gabarito'),
            'explicacao': a.get('explicacao', ''),
        })
        global_id += 1
    return result


if __name__ == '__main__':
    base = Path(__file__).parent.parent
    questoes = parse_questoes(base / 'questoes.md')
    gabarito = parse_gabarito(base / 'gabarito.md')
    data = build_json(questoes, gabarito)
    out = base / 'data' / 'questoes.json'
    out.parent.mkdir(exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'Gerado: {out} ({len(data)} questões)')
