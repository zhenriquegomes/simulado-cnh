"""
Scraper de questões do DETRAN SP.

Busca questões de https://detran.sp.gov.br/detran-prova/simulado_questoes/questoes.htm,
remove duplicatas em relação ao banco existente, preenche gabarito via Claude API
e baixa imagens referenciadas.

Uso:
    python3 scripts/scrape_detran.py            # modo normal
    python3 scripts/scrape_detran.py --dry-run  # mostra estatísticas sem salvar
"""

import re
import sys
import json
import time
import unicodedata
import argparse
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import anthropic

BASE_URL = "https://detran.sp.gov.br/detran-prova/simulado_questoes/questoes.htm"
IMG_BASE_URL = "https://detran.sp.gov.br/detran-prova/simulado_questoes/"
ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "questoes.json"
IMG_DEST = ROOT / "assets" / "detran"

BATCH_SIZE = 15
ALT_RE = re.compile(r"^([A-D])\)\s+(.+)", re.DOTALL)

# Padrões que indicam parágrafo de alternativas
ALT_DETECT_RE = re.compile(r"\bA\)\s.+\bB\)\s.+\bC\)\s.+\bD\)\s", re.DOTALL)

# Texto de navegação a ignorar
SKIP_PATTERNS = re.compile(r"^(©|DETRAN|Voltar|Início|Menu|Simulado|Questões|Prova)", re.IGNORECASE)


# ── normalização ──────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── extração de texto e imagem de um elemento ────────────────────────────────

def get_text_and_img(elem: Tag) -> tuple[str, str | None]:
    """Extrai texto e src da primeira imagem do elemento."""
    img_src = None
    parts = []
    for child in elem.descendants:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag) and child.name == "img":
            src = child.get("src", "")
            if src and img_src is None:
                img_src = src.strip()
    text = " ".join(parts)
    text = re.sub(r"\s+", " ", text).strip()
    # Limpar artefatos de vírgulas/espaços ao redor de imagens removidas
    text = re.sub(r",\s*,", ",", text)
    text = text.lstrip(", ").strip()
    return text, img_src


# ── extração de alternativas de um parágrafo com <br/> ───────────────────────

def parse_alternatives(elem: Tag) -> dict[str, str]:
    """Extrai alternativas A-D de um <p> com separadores <br/>."""
    # Montar texto com \n nos <br/>
    parts: list[str] = []
    for child in elem.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag):
            if child.name == "br":
                parts.append("\n")
            else:
                parts.append(child.get_text(" ", strip=True))

    full = "".join(parts)
    alts: dict[str, str] = {}
    for line in full.splitlines():
        m = ALT_RE.match(line.strip())
        if m:
            letra, texto = m.group(1), m.group(2).strip()
            if letra not in alts:
                alts[letra] = texto
    return alts


# ── parsing da página ─────────────────────────────────────────────────────────

def fetch_page() -> BeautifulSoup:
    print("Buscando página do DETRAN SP...")
    resp = requests.get(BASE_URL, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return BeautifulSoup(resp.text, "html.parser")


def parse_questions(soup: BeautifulSoup) -> list[dict]:
    """
    Extrai todas as questões da página.

    Estrutura real da página:
    - Enunciados: em <h5> OU em <p> (ambos com texto da pergunta)
    - Alternativas: sempre em <p> único com A) B) C) D) separados por <br/>
    """
    questions: list[dict] = []
    current: dict | None = None

    for elem in soup.find_all(["h5", "p"]):
        raw = elem.get_text(" ", strip=True)
        if not raw:
            continue

        # Elemento de alternativas: contém A) B) C) D) em sequência
        if ALT_DETECT_RE.search(raw):
            if current is not None:
                alts = parse_alternatives(elem)
                if len(alts) == 4:
                    current["alternativas"] = alts
                    questions.append(current)
                current = None
            continue

        # Elemento de enunciado
        text, img_src = get_text_and_img(elem)
        text = text.strip()

        # Filtrar textos de navegação / muito curtos
        if len(text) < 10 or SKIP_PATTERNS.match(text):
            continue

        # Começar nova questão (descartando a anterior se incompleta)
        current = {"enunciado": text, "img_src": img_src, "alternativas": {}}

    return questions


# ── deduplicação ──────────────────────────────────────────────────────────────

def load_existing() -> tuple[list, set]:
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    existing_norm = {normalize(q["enunciado"]) for q in data}
    return data, existing_norm


def filter_new(questions: list[dict], existing_norm: set) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for q in questions:
        norm = normalize(q["enunciado"])
        if norm in existing_norm or norm in seen:
            continue
        seen.add(norm)
        result.append(q)
    return result


# ── download de imagens ───────────────────────────────────────────────────────

def download_image(src: str) -> str | None:
    IMG_DEST.mkdir(parents=True, exist_ok=True)
    url = urljoin(IMG_BASE_URL, src)
    filename = Path(src).name
    dest = IMG_DEST / filename
    if dest.exists():
        return f"assets/detran/{filename}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return f"assets/detran/{filename}"
    except Exception as e:
        print(f"  ⚠  Falha ao baixar {url}: {e}")
        return None


# ── gabarito via Claude ───────────────────────────────────────────────────────

def build_batch_prompt(batch: list[dict]) -> str:
    lines = [
        "Você é especialista no CTB (Código de Trânsito Brasileiro).",
        "Para cada questão abaixo, indique APENAS a letra da resposta correta (A, B, C ou D).",
        'Responda SOMENTE com JSON no formato: {"1": "A", "2": "C", ...}',
        "",
    ]
    for i, q in enumerate(batch, 1):
        lines.append(f"{i}. {q['enunciado']}")
        for letra, texto in q["alternativas"].items():
            lines.append(f"   {letra}) {texto}")
        lines.append("")
    return "\n".join(lines)


def get_gabariots_batch(batch: list[dict], client: anthropic.Anthropic) -> list[str]:
    prompt = build_batch_prompt(batch)
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        m = re.search(r"\{[^}]+\}", raw, re.DOTALL)
        if not m:
            raise ValueError(f"Resposta inesperada: {raw[:200]}")
        data = json.loads(m.group())
        return [data.get(str(i), "A") for i in range(1, len(batch) + 1)]
    except Exception as e:
        print(f"  ⚠  Erro ao obter gabarito: {e}. Usando 'A' como placeholder.")
        return ["A"] * len(batch)


def fill_gabariots(questions: list[dict]) -> list[str]:
    client = anthropic.Anthropic()
    gabariots: list[str] = []
    total = len(questions)
    for i in range(0, total, BATCH_SIZE):
        batch = questions[i : i + BATCH_SIZE]
        end = min(i + BATCH_SIZE, total)
        print(f"  Gabarito {i+1}–{end} / {total}...", end=" ", flush=True)
        batch_ans = get_gabariots_batch(batch, client)
        gabariots.extend(batch_ans)
        print("✓")
        if end < total:
            time.sleep(0.5)
    return gabariots


# ── montar questões finais ────────────────────────────────────────────────────

def build_entries(new_questions: list[dict], gabariots: list[str], start_id: int) -> list[dict]:
    entries: list[dict] = []
    for i, (q, gab) in enumerate(zip(new_questions, gabariots)):
        imagem = None
        if q["img_src"]:
            print(f"  Baixando imagem: {q['img_src']}...", end=" ", flush=True)
            imagem = download_image(q["img_src"])
            print("✓" if imagem else "✗")

        entries.append({
            "id": start_id + i,
            "parte": 2,
            "modulo": 5,
            "modulo_nome": "DETRAN SP",
            "dificuldade": "Intermediário",
            "enunciado": q["enunciado"],
            "codigo_placa": None,
            "imagem_placa": imagem,
            "alternativas": q["alternativas"],
            "gabarito": gab,
            "explicacao": "",
        })
    return entries


# ── main ──────────────────────────────────────────────────────────────────────

def fix_gabarito_mode():
    """Re-preenche gabarito via Claude API para todas as questões do módulo 5 (DETRAN SP)."""
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    detran = [q for q in data if q.get("modulo") == 5]
    if not detran:
        print("Nenhuma questão do módulo 5 encontrada.")
        return

    print(f"Corrigindo gabarito de {len(detran)} questões DETRAN SP...")
    gabariots = fill_gabariots(detran)

    id_to_gab = {q["id"]: gab for q, gab in zip(detran, gabariots)}
    for q in data:
        if q["id"] in id_to_gab:
            q["gabarito"] = id_to_gab[q["id"]]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Gabarito corrigido para {len(detran)} questões.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Mostra estatísticas sem salvar")
    parser.add_argument("--fix-gabarito", action="store_true", help="Re-preenche gabarito das questões DETRAN SP via Claude API")
    args = parser.parse_args()

    if args.fix_gabarito:
        fix_gabarito_mode()
        return

    soup = fetch_page()
    raw_questions = parse_questions(soup)
    print(f"Questões encontradas na página:  {len(raw_questions)}")

    existing_data, existing_norm = load_existing()
    new_questions = filter_new(raw_questions, existing_norm)
    duplicates = len(raw_questions) - len(new_questions)
    print(f"Duplicatas removidas:            {duplicates}")
    print(f"Questões novas a adicionar:      {len(new_questions)}")

    if not new_questions:
        print("Nenhuma questão nova encontrada. Banco já está atualizado.")
        return

    if args.dry_run:
        print("\n[dry-run] Nenhuma alteração salva.")
        imgs = sum(1 for q in new_questions if q["img_src"])
        print(f"  Questões com imagem: {imgs}")
        for q in new_questions[:5]:
            print(f"  • {q['enunciado'][:80]}... img={q['img_src']}")
        return

    print("\nPreenchendo gabarito via Claude API...")
    gabariots = fill_gabariots(new_questions)

    print("\nMontando e salvando questões...")
    start_id = max(q["id"] for q in existing_data) + 1
    entries = build_entries(new_questions, gabariots, start_id)

    updated = existing_data + entries
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Banco atualizado: {len(existing_data)} → {len(updated)} questões (+{len(entries)})")


if __name__ == "__main__":
    main()
