"""Candidates from the visually checked glossary spreads in the INALI writing norm.

The PDF text layer loses underlining under vowels; every row requires a visual
orthographic review before training. This script preserves the visible pairing
and separates listed synonyms, but does not claim the exact regional variant.
"""
import csv
import argparse
import re
import unicodedata
from pathlib import Path
import pdfplumber

parser = argparse.ArgumentParser(description='Extrae candidatos del glosario de la norma INALI.')
parser.add_argument('--pdf', required=True, type=Path, help='Ruta al PDF de la norma')
parser.add_argument('--out', required=True, type=Path, help='Ruta del CSV de salida')
args = parser.parse_args()
SRC = args.pdf
OUT = args.out
TITLE="Njaua nt'ot'i ra hñähñu. Norma de escritura de la lengua Hñähñu (otomí)"
VARIANT="hñähñu: múltiples variantes; variante de cada forma no indicada"

def norm(s):
    return unicodedata.normalize('NFC', re.sub(r'\s+',' ',s.strip()))

def lines(page, split, ymin, ymax):
    left=page.crop((65,ymin,split,ymax)).extract_text_lines()
    right=page.crop((split,ymin,340,ymax)).extract_text_lines()
    return left,right

def synonym_groups(page, split, ymin, ymax):
    left,right=lines(page,split,ymin,ymax)
    pending=[]
    groups=[]
    for l in left:
        m=next((r for r in right if abs(r['top']-l['top'])<0.7),None)
        if m:
            groups.append([norm(' '.join(pending+[l['text']])),norm(m['text']),l['top']])
            pending=[]
        else:
            pending.append(l['text'])
    # Right-only lines are continuation of previous Spanish definition.
    for r in right:
        if not any(abs(r['top']-l['top'])<0.7 for l in left) and groups:
            prior=[g for g in groups if g[2] < r['top']]
            if prior: prior[-1][1]+=' '+norm(r['text'])
    return [(a,b) for a,b,_ in groups]

def new_word_groups(page):
    left,right=lines(page,215,209,480)
    groups=[]
    for l in left:
        m=next((r for r in right if abs(r['top']-l['top'])<0.7),None)
        if m: groups.append([norm(l['text']),norm(m['text']),l['top']])
    for r in right:
        if not any(abs(r['top']-l['top'])<0.7 for l in left) and groups:
            prior=[g for g in groups if g[2] < r['top']]
            if prior: prior[-1][1]+=' '+norm(r['text'])
    return [(a,b) for a,b,_ in groups]

out=[]
seen=set()
def append(es,oto,page,category):
    es,oto=norm(es),norm(oto)
    if not es or not oto or '�' in es+oto: return
    key=(es.casefold(),oto.casefold())
    if key in seen: return
    seen.add(key)
    out.append(dict(
        espanol=es,otomi=oto,variante=VARIANT,categoria=category,
        contexto='sinónimo según variante' if category=='sinónimos entre variantes' else 'neologismo',
        nombre_cientifico='',calidad_tradicional='',fuente=TITLE,pagina_pdf=page,
        estado_revision='pendiente',
        notas='Revisar la grafía en el PDF: la extracción pierde el subrayado de algunas vocales. Confirmar variante regional con hablantes.'
    ))

with pdfplumber.open(SRC) as pdf:
    for p,split,ymin,ymax in [(206,250,100,475),(207,250,45,475),(208,220,45,485),(209,215,45,150)]:
        for oto_list,es in synonym_groups(pdf.pages[p-1],split,ymin,ymax):
            if p==206 and es=='o pato': es='pato'
            if es in {'denota respeto o diminutivo'}: continue  # morphemes, not lexical translations
            for form in oto_list.split(','):
                append(es,form,p,'sinónimos entre variantes')
    for es,oto_list in new_word_groups(pdf.pages[208]):
        for form in oto_list.split(','):
            append(es,form,209,'palabras nuevas')

OUT.parent.mkdir(parents=True,exist_ok=True)
fields=['espanol','otomi','variante','categoria','contexto','nombre_cientifico','calidad_tradicional','fuente','pagina_pdf','estado_revision','notas']
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
print('Wrote',len(out),'rows to',OUT)
