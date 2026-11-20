"""Fábrica de ideas creativas: valida las fichas de una ronda y arma su página.

  validar  revisa la forma de cada ficha (campos, longitud, público, persuasión, proceso), los vetos de marca en la
           escena (C31 a C33) y que las fichas de un mismo ítem no repitan estrategia ni concepto.
  pagina   arma la página del celular: los ítems de la editorial y, bajo cada uno, sus conceptos numerados.

Uso (desde labs/motor-piezas):
  python creativas/creativas.py validar --ronda creativas/rondas/C01.json
  python creativas/creativas.py pagina --ronda creativas/rondas/C01.json --salida <ruta.html>
"""
import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
LAB = AQUI.parent
sys.path.insert(0, str(LAB / 'ideas'))
from ideas import norm, palabras  # noqa: E402

OBLIGATORIOS = ['item', 'titulo', 'concepto', 'escena', 'relacion', 'estrategia', 'publico', 'persuasion',
                'gancho_visual', 'proceso', 'evitar', 'riesgo']
PUBLICOS = {'alumno', 'seguidor', 'cliente'}
# vetos de marca en la escena (C31-C33 y la plantilla de metáforas); se ignora lo que va después de «sin»
VETOS_ESCENA = (r'\b(personas?|gente|hombres?|mujer(es)?|trabajador\w*|obreros?|ingenier[oa]s?|manos?|pantallas?|'
                r'monitor\w*|computador\w*|celular\w*|texto|letras?|numeros?|cifras?|logos?|robots?|cerebros?|chips?|'
                r'flechas?|hologram\w*|brill\w*|resplandor\w*|degradad\w*|foto\w*|render\w*|neon)\b')
YA_USADOS = r'\b(cremallera|ciudad que se vuelve red|tuberia que cruza)'


def validar_ficha(f: dict, items: dict) -> tuple[list, list]:
    E, A = [], []
    for c in OBLIGATORIOS:
        v = f.get(c)
        if not v or (isinstance(v, dict) and not any(v.values())):
            E.append(f'falta «{c}»')
    if E:
        return E, A
    if f['item'] not in items:
        E.append(f"el ítem «{f['item']}» no está en la ronda")
    n = len(f['escena'].split())
    if not 40 <= n <= 120:
        A.append(f'escena de {n} palabras (de 40 a 120)')
    sin_negaciones = re.sub(r'\bsin [^.;:]*', ' ', norm(f['escena']))
    m = re.search(VETOS_ESCENA, sin_negaciones)
    if m:
        E.append(f'veto de marca en la escena: «{m.group(0)}» (C31-C33)')
    if re.search(YA_USADOS, norm(f['concepto'] + ' ' + f['escena'])):
        A.append('reutiliza una metáfora ya vista en el laboratorio o en la editorial')
    p = f['publico']
    if not isinstance(p, dict) or norm(p.get('tipo', '')) not in PUBLICOS or not p.get('quien'):
        E.append('público sin tipo (alumno, seguidor o cliente) o sin quién')
    n = len(f['persuasion'].split())
    if not 6 <= n <= 35:
        A.append(f'persuasión de {n} palabras (de 6 a 35, una frase)')
    if not isinstance(f['proceso'], list) or not 3 <= len(f['proceso']) <= 7:
        E.append('el proceso va como lista de 3 a 7 pasos')
    return E, A


def o_validar(a):
    ronda = json.loads(Path(a.ronda).read_text(encoding='utf-8'))
    items = {i['id']: i for i in ronda['items']}
    validas = 0
    for f in ronda['fichas']:
        E, A = validar_ficha(f, items)
        f['validacion'] = {'errores': E, 'avisos': A}
        validas += not E
        print(f"{'ok   ' if not E else 'FALLA'} {f['id']:9s} {f['titulo'][:60]}")
        for x in E:
            print('        -', x)
        for x in A:
            print('        aviso:', x)
    avisos = []
    for iid in items:
        fs = [f for f in ronda['fichas'] if f.get('item') == iid and not f['validacion']['errores']]
        est = [norm(f['estrategia']) for f in fs]
        for e in {x for x in est if est.count(x) > 1}:
            avisos.append(f'{iid}: estrategia repetida «{e}»')
        for i in range(len(fs)):
            for j in range(i + 1, len(fs)):
                x, y = palabras(fs[i]['concepto']), palabras(fs[j]['concepto'])
                if x and y and len(x & y) / len(x | y) > 0.35:
                    avisos.append(f"{fs[i]['id']} y {fs[j]['id']} cuentan casi lo mismo")
    ronda['monotonia'] = avisos
    for x in avisos:
        print('monotonía:', x)
    Path(a.ronda).write_text(json.dumps(ronda, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f"{validas}/{len(ronda['fichas'])} fichas pasan la validación")
    return 0 if validas else 1


def o_pagina(a):
    ronda = json.loads(Path(a.ronda).read_text(encoding='utf-8'))
    por_id = {f['id']: f for f in ronda['fichas']}
    e = html.escape
    fuentes = LAB / 'salida' / 'G28' / 'fuentes'
    f64 = lambda n: base64.b64encode((fuentes / n).read_bytes()).decode()
    tipos = {'alumno': 'Potenciales alumnos', 'seguidor': 'Seguidores en LinkedIn', 'cliente': 'Potenciales clientes'}
    secciones, n = [], 0
    for it in ronda['items']:
        tarjetas = []
        for fid in ronda['presentadas'].get(it['id'], []):
            n += 1
            f = por_id[fid]
            p = f['publico']
            filas = [
                ('La idea creativa', e(f['concepto'])),
                ('Lo que se ve', e(f['escena'])),
                ('Cómo representa la idea del post', e(f['relacion'])),
                ('Para quién', f"<b>{e(tipos.get(norm(p['tipo']), p['tipo']))}:</b> {e(p['quien'])}"),
                ('Persuasión', e(f['persuasion'])),
                ('Lo primero que se ve en el feed', e(f['gancho_visual'])),
                ('El proceso', '<ol>' + ''.join(f'<li>{e(x)}</li>' for x in f['proceso']) + '</ol>'),
                ('Cuidado', e(f['riesgo'])),
            ]
            cuerpo = ''.join(f'<div class="fila"><dt>{k}</dt><dd>{v}</dd></div>' for k, v in filas)
            tarjetas.append(f'<section class="alt" id="c{n}"><h3><span class="num">{n}</span><span>{e(f["titulo"])}</span>'
                            f'</h3><dl>{cuerpo}</dl></section>')
        secciones.append(f'<section class="item"><div class="cab"><p class="kick">Post de la editorial · '
                         f'{e(it.get("etapa") or "sin etapa")}</p><h2>{e(it["titulo"])}</h2><p>{e(it["idea"])}</p></div>'
                         + ''.join(tarjetas) + '</section>')
    doc = f"""<title>{e(ronda['id'])} · Ideas creativas</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
@font-face {{ font-family: "Inter"; font-weight: 400; font-display: swap; src: url(data:font/woff2;base64,{f64('Inter-Regular.woff2')}) format("woff2"); }}
@font-face {{ font-family: "Inter"; font-weight: 600; font-display: swap; src: url(data:font/woff2;base64,{f64('Inter-SemiBold.woff2')}) format("woff2"); }}
:root {{ --bg:#FAFAF9; --sup:#FFFFFF; --tx:#1F2328; --mu:#5B636E; --bo:#E2E3DF; --pt:#074E43;
  --texto: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#111418; --sup:#1A1F24; --tx:#ECEDEE; --mu:#9BA3AD; --bo:#262B31; --pt:#99F6E4; color-scheme: dark }} }}
:root[data-theme="dark"] {{ --bg:#111418; --sup:#1A1F24; --tx:#ECEDEE; --mu:#9BA3AD; --bo:#262B31; --pt:#99F6E4; color-scheme: dark }}
body {{ background: var(--bg); color: var(--tx); font-family: var(--texto); font-size: 16px; line-height: 1.55; margin: 0; }}
main {{ max-width: 760px; margin: 0 auto; padding-block: 20px 48px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 32px; }}
h1 {{ font-size: 1.35rem; font-weight: 600; margin: 0; text-wrap: balance; }}
header {{ display: grid; gap: 10px; }}
header p {{ margin: 0; color: var(--mu); }}
.caja {{ background: var(--sup); border: 1px solid var(--bo); border-radius: 8px; padding: 12px 14px; }}
.caja p {{ margin: 0; color: var(--tx); }}
.item {{ display: grid; gap: 22px; }}
.cab {{ background: var(--sup); border: 1px solid var(--bo); border-radius: 8px; padding: 14px 16px; display: grid; gap: 6px; }}
.cab h2 {{ font-size: 1.15rem; font-weight: 600; margin: 0; text-wrap: balance; }}
.cab p {{ margin: 0; color: var(--mu); }}
.kick {{ font-size: .78rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--pt) !important; }}
.alt {{ display: grid; gap: 10px; border-top: 1px solid var(--bo); padding-top: 16px; }}
h3 {{ display: flex; gap: 12px; align-items: center; font-size: 1.08rem; font-weight: 600; margin: 0; }}
.num {{ flex: none; display: inline-grid; place-items: center; width: 2.2em; height: 2.2em; border-radius: 50%; background: var(--pt); color: var(--bg); }}
dl {{ margin: 0; display: grid; gap: 10px; }}
.fila {{ display: grid; gap: 2px; }}
dt {{ font-size: .78rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--pt); }}
dd {{ margin: 0; }}
dd ol {{ margin: 0; padding-left: 1.2em; display: grid; gap: 3px; }}
footer {{ color: var(--mu); font-size: .9rem; border-top: 1px solid var(--bo); padding-top: 14px; }}
</style>
<main>
  <header>
    <h1>{e(ronda['id'])} · Ideas creativas para {len(ronda['items'])} posts de la editorial</h1>
    <p>{e(ronda.get('intro', ''))}</p>
    <div class="caja"><p><b>Cómo responder:</b> por cada post, el número del concepto que llevarías a imagen y una frase de por qué. Vale también «ninguno» con el motivo. Los jueces ya votaron; su voto te lo muestro después.</p></div>
  </header>
  {''.join(secciones)}
  <footer>Laboratorio del motor de piezas: ideas creativas en texto, sin imágenes ni créditos. No publicar.</footer>
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
    p.add_argument('--salida', required=True)
    a = ap.parse_args()
    sys.exit({'validar': o_validar, 'pagina': o_pagina}[a.orden](a) or 0)


if __name__ == '__main__':
    main()
