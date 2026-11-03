"""Extract structured bilingual candidates from the appended tables of the UAQ book."""
import csv
import argparse
import json
import re
import unicodedata
from pathlib import Path

import pdfplumber

parser = argparse.ArgumentParser(description="Extrae candidatos bilingües de los apéndices del libro de UAQ.")
parser.add_argument("--pdf", required=True, type=Path, help="Ruta al PDF original")
parser.add_argument("--out", required=True, type=Path, help="Ruta del CSV de salida")
parser.add_argument("--existing-jsonl", type=Path, help="Dataset existente para marcar traducciones distintas")
args = parser.parse_args()
SOURCE = args.pdf
OUT = args.out
TITLE = "Ar ñäñho hongar nzaki. El otomí en busca de la vida"
VARIANT = "ñäñho (Santiago Mexquititlán y San Ildefonso Tultepec, Amealco, Querétaro)"
rows = []
seen = set()


def clean(s):
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", (s or "").strip()))


def add(es, oto, page, category, context="", note="", scientific="", quality=""):
    es, oto = clean(es), clean(oto)
    if not es or not oto or "�" in es + oto:
        return
    key = (es.casefold(), oto.casefold(), context.casefold())
    if key in seen:
        return
    seen.add(key)
    flags = []
    if "/" in oto or "," in oto or " o " in oto or "(" in oto:
        flags.append("Contiene variantes o explicación; separar tras revisión.")
    if es.casefold() == oto.casefold():
        flags.append("Posible préstamo o forma idéntica; verificar.")
    rows.append({
        "espanol": es,
        "otomi": oto,
        "variante": VARIANT,
        "categoria": category,
        "contexto": context,
        "nombre_cientifico": clean(scientific),
        "calidad_tradicional": quality,
        "fuente": TITLE,
        "pagina_pdf": page,
        "estado_revision": "pendiente",
        "notas": " ".join([x for x in [note, *flags] if x]),
    })


def table_rows(pdf):
    for page_no in range(359, 368):
        for table_idx, table in enumerate(pdf.pages[page_no - 1].extract_tables()):
            if page_no <= 364 and table_idx == 0:
                category = "plantas y herbolaria"
            elif (page_no == 364 and table_idx == 1) or page_no == 365:
                category = "fauna y medicina tradicional"
            else:
                category = "líquidos, alimentos y minerales"
            for cells in table:
                if not cells or len(cells) < 2:
                    continue
                es, oto = clean(cells[0]), clean(cells[1])
                if not es or not oto or "Nombre en" in oto or "CALIDAD" in es or es.startswith("Líquidos,"):
                    continue
                scientific = cells[2] if category == "plantas y herbolaria" and len(cells) > 2 else ""
                offset = 3 if category == "plantas y herbolaria" else 2
                quality = ""
                if len(cells) > offset and clean(cells[offset]).lower() == "x":
                    quality = "caliente"
                if len(cells) > offset + 1 and clean(cells[offset + 1]).lower() == "x":
                    quality = "frío" if not quality else "caliente/frío: revisar"
                add(es, oto, page_no, category, scientific=scientific, quality=quality)


def kinship_rows(pdf):
    for page_no in (368, 369, 370):
        table = pdf.pages[page_no - 1].extract_tables()[0]
        for cells in table:
            if len(cells) != 4:
                continue
            es = clean(cells[0])
            if es in {"Estado civil", "Compadrazgo"} or es.lower().startswith("término"):
                continue
            for index, context in ((1, "genérico"), (2, "entre hombres"), (3, "entre mujeres")):
                oto = clean(cells[index])
                if oto:
                    add(es, oto, page_no, "parentesco y estado civil", context)


def split_lines(page, top_min, top_max, split):
    left = page.crop((80, top_min, split, top_max)).extract_text_lines()
    right = page.crop((split, top_min, 430, top_max)).extract_text_lines()
    return left, right


def glossary_rows(pdf):
    ranges = ((370, 335, 580), (371, 65, 580), (372, 65, 580), (373, 65, 145), (373, 185, 245))
    for page_no, y0, y1 in ranges:
        page = pdf.pages[page_no - 1]
        left, right = split_lines(page, y0, y1, 190)
        pending = []
        for line in left:
            match = next((r for r in right if abs(r["top"] - line["top"]) < 1.0), None)
            if not match:
                pending.append(line["text"])
                continue
            oto = clean(" ".join(pending + [line["text"]]))
            pending.clear()
            category = "direcciones" if page_no == 373 and y0 > 180 else "vocabulario general"
            add(match["text"], oto, page_no, category)


def reversed_rows(pdf):
    for page_no, y0, y1, category in (
        (373, 290, 580, "cuerpo humano"),
        (374, 65, 115, "cuerpo humano"),
        (374, 155, 430, "milpa y maíz"),
    ):
        page = pdf.pages[page_no - 1]
        words = [w for w in page.extract_words() if y0 <= w["top"] < y1 and 80 <= w["x0"] < 430]
        groups = {}
        for w in words:
            y = round(w["top"] / 15) * 15
            groups.setdefault(y, []).append(w)
        for group in groups.values():
            group.sort(key=lambda w: w["x0"])
            es = " ".join(w["text"] for w in group if w["x0"] < 180)
            oto = " ".join(w["text"] for w in group if w["x0"] >= 180)
            add(es, oto, page_no, category)


with pdfplumber.open(SOURCE) as pdf:
    table_rows(pdf)
    kinship_rows(pdf)
    glossary_rows(pdf)
    reversed_rows(pdf)

if args.existing_jsonl:
    existing = {}
    for line in args.existing_jsonl.open(encoding="utf-8"):
        pair = json.loads(line)["traductor"]
        existing.setdefault(clean(pair["es"]).casefold(), set()).add(clean(pair["oto"]).casefold())
    for row in rows:
        old = existing.get(row["espanol"].casefold())
        if old and row["otomi"].casefold() not in old:
            row["notas"] = clean(row["notas"] + " Traducción distinta en el dataset existente; revisar variante y sentido.")

OUT.parent.mkdir(parents=True, exist_ok=True)
fields = ["espanol", "otomi", "variante", "categoria", "contexto", "nombre_cientifico", "calidad_tradicional", "fuente", "pagina_pdf", "estado_revision", "notas"]
with OUT.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {len(rows)} rows to {OUT}")
