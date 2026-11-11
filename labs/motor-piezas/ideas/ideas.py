"""Fábrica de ideas del motor de piezas: valida fichas y arma la página de una ronda.

  validar  revisa la forma de cada ficha de una ronda (rondas/I01.json): los rechazos de QA de la editorial de UAS
           (campo faltante, voz de operador, andamiaje en el arco, cadena de la tesis mal formada) y las reglas de
           verdad y de voz de `raiz-david.yaml`. Revisa también la monotonía de la ronda (tesis repetidas).
  pagina   arma la página del celular con las ideas numeradas, sin el voto de los jueces.

Uso (desde labs/motor-piezas):
  python ideas/ideas.py validar --ronda ideas/rondas/I01.json
  python ideas/ideas.py pagina --ronda ideas/rondas/I01.json --elegidas 3,7,9,12 --salida <ruta.html>
"""
import argparse
import base64
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

AQUI = Path(__file__).resolve().parent
LAB = AQUI.parent
RAIZ = yaml.safe_load((AQUI / 'raiz-david.yaml').read_text(encoding='utf-8'))

OBLIGATORIOS = ['titulo', 'tema', 'manantial', 'formula', 'evidencia', 'premisa', 'hipotesis', 'respuesta', 'cadena_tesis',
                'residuo', 'gancho', 'arco', 'escena', 'arquitectura', 'pilar', 'audiencia', 'canales', 'procedencia']
MANANTIALES = {'experiencia', 'dolor', 'senal', 'señal', 'pilar'}
FORMULAS = {'experiencia_a_criterio', 'senal_a_angulo', 'sintesis', 'contraria', 'traduccion'}
GANCHOS = {'creencia equivocada', 'error caro', 'dolor oculto', 'contraste', 'mecanismo real', 'diagnostico', 'diagnóstico'}
ARQUITECTURAS = {'postura', 'dolor', 'transformacion', 'transformación', 'comparacion', 'comparación'}
VOZ_OPERADOR = r'\b(la editorial propone|proponemos|umbral propone|esta pieza|este post|el artículo propone)\b'
ANDAMIAJE = r'(^|[.;]\s*)(parte de|tensiona|llega a que)\b'
ETIQUETAS_PROCESO = r'\b(tesis editorial|claim|hitl|payload|v1|v2|salto editorial|lectura editorial)\b'
CIFRAS = r'\d+\s*(%|por ciento|veces|x\b|horas|h\b|minutos|dias|semanas|meses|anos)|\broi\b|\bmas de \d+'   # sobre texto sin tildes
CLIENTES_NO_V6 = r'\b(wsp|comgrap|dessau|tedi|konstruedu|borag[oó]|cmp|pelambres|wolnitzky|enjofra)\b'
CONTRASTE_VETADO = r'\b(tu problema no es|no es (solo|sólo) )'


def norm(t: str) -> str:
    t = unicodedata.normalize('NFD', t or '')
    return ''.join(c for c in t if not unicodedata.combining(c)).lower()


def texto_de(f: dict) -> str:
    partes = []
    for v in f.values():
        if isinstance(v, dict):
            partes += [str(x) for x in v.values()]
        elif isinstance(v, list):
            partes += [str(x) for x in v]
        else:
            partes.append(str(v))
    return ' '.join(partes)


def validar_ficha(f: dict) -> tuple[list, list]:
    E, A = [], []
    for c in OBLIGATORIOS:
        v = f.get(c)
        if not v or (isinstance(v, dict) and not any(v.values())):
            E.append(f'falta «{c}»')
    if E:
        return E, A
    if norm(f['manantial']) not in {norm(m) for m in MANANTIALES}:
        E.append(f"manantial «{f['manantial']}» no es experiencia, dolor, señal ni pilar")
    if f['formula'] not in FORMULAS:
        A.append(f"fórmula «{f['formula']}» fuera de la lista")
    if norm(f['arquitectura']) not in {norm(a) for a in ARQUITECTURAS}:
        A.append(f"arquitectura «{f['arquitectura']}» fuera del selector")
    ev = f['evidencia']
    if not isinstance(ev, dict) or not ev.get('referencia'):
        E.append('la evidencia no trae referencia concreta')
    # premisa: postura, sin voz de operador ni pregunta
    p = f['premisa']
    if re.search(VOZ_OPERADOR, norm(p)):
        E.append('premisa con voz de operador')
    if p.strip().endswith('?') or p.strip().startswith('¿'):
        E.append('la premisa es una pregunta, no una postura')
    n = len(p.split())
    if not 8 <= n <= 50:
        A.append(f'premisa de {n} palabras (de 8 a 50)')
    if norm(f['hipotesis']).strip() == norm(f['respuesta']).strip():
        E.append('la hipótesis y la respuesta son iguales: no hay tensión')
    # cadena de la tesis
    ct = f['cadena_tesis']
    if not isinstance(ct, dict) or not all(ct.get(k) for k in ('evidencia', 'inferencia', 'salto', 'no_afirmado')):
        E.append('cadena de la tesis incompleta (evidencia, inferencia, salto, no afirmado)')
    elif norm(ct['salto'])[:40] and norm(ct['salto'])[:40] in norm(ct['evidencia']):
        E.append('el salto editorial se coló en la evidencia')
    # arco: con estrategia entre paréntesis, sin andamiaje ni etiquetas de proceso
    arco = f['arco']
    for marca in ('(punto de partida:', '(tensión:', '(cierre:'):
        if marca not in norm(arco).replace('tension', 'tensión'):
            A.append(f'el arco no marca {marca}…)')
    if re.search(ANDAMIAJE, norm(re.sub(r'\([^)]*\)', '', arco))):
        E.append('arco con andamiaje («Parte de… / Tensiona… / Llega a que…» como verbo principal)')
    if re.search(ETIQUETAS_PROCESO, norm(re.sub(r'\([^)]*\)', '', arco + ' ' + p))):
        E.append('etiquetas de proceso en el arco o la premisa')
    # gancho
    g = f['gancho']
    if not isinstance(g, dict) or not g.get('texto'):
        E.append('gancho sin texto')
    else:
        if norm(g.get('tipo', '')) not in {norm(x) for x in GANCHOS}:
            A.append(f"tipo de gancho «{g.get('tipo')}» fuera de la lista")
        if g['texto'].strip().startswith('¿'):
            A.append('el gancho abre con pregunta (la voz de David abre con una afirmación)')
    # verdad y voz, sobre todo el texto de la ficha
    todo = texto_de(f)
    m = re.search(CIFRAS, norm(todo))
    if m:
        E.append(f'cifra sin confirmar («{m.group(0)}»): el CV v6 no trae cifras de resultados')
    m = re.search(CLIENTES_NO_V6, norm(todo))
    if m:
        E.append(f'nombra un cliente que el CV v6 no nombra («{m.group(0)}»)')
    m = re.search(CONTRASTE_VETADO, norm(todo))
    if m:
        E.append(f'fórmula vetada «{m.group(0).strip()}…» (benchmark de voz de UAS)')
    for frase in RAIZ['lista_negra']['frases']:
        if norm(frase) in norm(todo):
            E.append(f'lista negra: «{frase}»')
    if re.search(r'\b(vosotros|os |vuestro|dedicais|queres)\b', norm(todo)):
        E.append('persona gramatical: se usa «ustedes»')
    return E, A


def palabras(t: str) -> set:
    return {w for w in re.findall(r'[a-zñ]{5,}', norm(t))}


def monotonia(fichas: list) -> list:
    """Pares de ideas con la respuesta casi igual, y la tesis de UAS repetida."""
    avisos = []
    for i in range(len(fichas)):
        for j in range(i + 1, len(fichas)):
            a, b = palabras(fichas[i]['respuesta']), palabras(fichas[j]['respuesta'])
            if a and b and len(a & b) / len(a | b) > 0.35:
                avisos.append(f"{fichas[i]['id']} y {fichas[j]['id']} sostienen casi lo mismo")
    uas = [f['id'] for f in fichas if 'criterio' in norm(f['respuesta']) and 'automatiz' in norm(f['respuesta'])]
    if len(uas) > 1:
        avisos.append(f"{len(uas)} ideas vuelven a «criterio antes que automatizar»: {', '.join(uas)}")
    return avisos


def o_validar(a):
    ronda = json.loads(Path(a.ronda).read_text(encoding='utf-8'))
    fichas = ronda['fichas']
    validas = 0
    for f in fichas:
        E, A = validar_ficha(f)
        f['validacion'] = {'errores': E, 'avisos': A}
        validas += not E
        estado = 'ok   ' if not E else 'FALLA'
        print(f"{estado} {f['id']:7s} {f['titulo'][:60]}")
        for x in E:
            print('        -', x)
        for x in A:
            print('        aviso:', x)
    mono = monotonia([f for f in fichas if not f['validacion']['errores']])
    ronda['monotonia'] = mono
    for x in mono:
        print('monotonía:', x)
    Path(a.ronda).write_text(json.dumps(ronda, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{validas}/{len(fichas)} fichas pasan la validación')
    return 0 if validas else 1


def o_pagina(a):
    ronda = json.loads(Path(a.ronda).read_text(encoding='utf-8'))
    ids = a.elegidas.split(',')
    por_id = {f['id']: f for f in ronda['fichas']}
    e = html.escape
    fuentes = LAB / 'salida' / 'G28' / 'fuentes'
    f64 = lambda n: base64.b64encode((fuentes / n).read_bytes()).decode()
    nombres_manantial = {'experiencia': 'tu experiencia', 'dolor': 'un dolor de tu audiencia', 'senal': 'una señal externa',
                         'señal': 'una señal externa', 'pilar': 'uno de tus pilares'}
    tarjetas = []
    for n, i in enumerate(ids, 1):
        f = por_id[i]
        ev = f['evidencia']
        canales = ''.join(f'<li><b>{e(k.capitalize() if k != "x" else "X")}:</b> {e(v)}</li>'
                          for k, v in f['canales'].items() if v)
        filas = [
            ('Lo que sostienes', e(f['premisa'])),
            ('Hipótesis → respuesta', f"<b>Se cree:</b> {e(f['hipotesis'])}<br><b>Tú respondes:</b> {e(f['respuesta'])}"),
            ('Gancho', e(f['gancho']['texto'])),
            ('La escena', e(f['escena'])),
            ('La frase que queda', e(f['residuo'])),
            ('De dónde sale', f"De {e(nombres_manantial.get(norm(f['manantial']), f['manantial']))}: {e(ev.get('referencia', ''))}. "
                              f"Pilar: {e(f['pilar'])}."),
            ('Contraargumento', e(f.get('contraargumento') or '—')),
            ('En cada canal', f'<ul>{canales}</ul>'),
        ]
        cuerpo = ''.join(f'<div class="fila"><dt>{k}</dt><dd>{v}</dd></div>' for k, v in filas)
        tarjetas.append(f'<section class="alt" id="i{n}"><h2><span class="num">{n}</span><span>{e(f["titulo"])}</span></h2>'
                        f'<dl>{cuerpo}</dl></section>')
    doc = f"""<title>{e(ronda['id'])} · Ideas</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
@font-face {{ font-family: "Inter"; font-weight: 400; font-display: swap; src: url(data:font/woff2;base64,{f64('Inter-Regular.woff2')}) format("woff2"); }}
@font-face {{ font-family: "Inter"; font-weight: 600; font-display: swap; src: url(data:font/woff2;base64,{f64('Inter-SemiBold.woff2')}) format("woff2"); }}
:root {{ --bg:#FAFAF9; --sup:#FFFFFF; --tx:#1F2328; --mu:#5B636E; --bo:#E2E3DF; --pt:#074E43;
  --texto: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#111418; --sup:#1A1F24; --tx:#ECEDEE; --mu:#9BA3AD; --bo:#262B31; --pt:#99F6E4; color-scheme: dark }} }}
:root[data-theme="dark"] {{ --bg:#111418; --sup:#1A1F24; --tx:#ECEDEE; --mu:#9BA3AD; --bo:#262B31; --pt:#99F6E4; color-scheme: dark }}
body {{ background: var(--bg); color: var(--tx); font-family: var(--texto); font-size: 16px; line-height: 1.55; margin: 0; }}
main {{ max-width: 760px; margin: 0 auto; padding-block: 20px 48px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 28px; }}
h1 {{ font-size: 1.35rem; font-weight: 600; margin: 0; text-wrap: balance; }}
header {{ display: grid; gap: 10px; }}
header p {{ margin: 0; color: var(--mu); }}
.caja {{ background: var(--sup); border: 1px solid var(--bo); border-radius: 8px; padding: 12px 14px; display: grid; gap: 6px; }}
.caja p {{ margin: 0; color: var(--tx); }}
.alt {{ display: grid; gap: 10px; border-top: 1px solid var(--bo); padding-top: 18px; }}
h2 {{ display: flex; gap: 12px; align-items: center; font-size: 1.15rem; font-weight: 600; margin: 0; }}
.num {{ flex: none; display: inline-grid; place-items: center; width: 2.2em; height: 2.2em; border-radius: 50%; background: var(--pt); color: var(--bg); }}
dl {{ margin: 0; display: grid; gap: 10px; }}
.fila {{ display: grid; gap: 2px; }}
dt {{ font-size: .78rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--pt); }}
dd {{ margin: 0; }}
dd ul {{ margin: 0; padding-left: 1.1em; display: grid; gap: 3px; }}
footer {{ color: var(--mu); font-size: .9rem; border-top: 1px solid var(--bo); padding-top: 14px; }}
</style>
<main>
  <header>
    <h1>{e(ronda['id'])} · Cuatro ideas tuyas</h1>
    <p>{e(ronda.get('intro', ''))}</p>
    <div class="caja">
      <p><b>Cómo responder:</b> el número de la que aprobarías y una frase de por qué. Para las demás vale «observar», «descartar» (con el motivo) o «archivar». Los jueces ya votaron; su voto te lo muestro después.</p>
    </div>
  </header>
  {''.join(tarjetas)}
  <footer>Fábrica de ideas del laboratorio del motor de piezas: no publicar.</footer>
</main>
"""
    destino = Path(a.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(doc, encoding='utf-8')
    print(destino, round(len(doc) / 1e3), 'KB')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='orden', required=True)
    v = sub.add_parser('validar')
    v.add_argument('--ronda', required=True)
    p = sub.add_parser('pagina')
    p.add_argument('--ronda', required=True)
    p.add_argument('--elegidas', required=True, help='ids de las fichas, en el orden en que se numeran')
    p.add_argument('--salida', required=True)
    a = ap.parse_args()
    sys.exit({'validar': o_validar, 'pagina': o_pagina}[a.orden](a) or 0)


if __name__ == '__main__':
    main()
