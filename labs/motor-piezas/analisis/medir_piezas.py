#!/usr/bin/env python3
"""Mide las seis piezas elegidas por David (v1 1°; v2 1°, 12°, 20°, 22°, 24°).

Medir, no mirar: tamaños en px del lienzo y en px CSS del celular, márgenes,
vacíos, relación de la ilustración o la imagen con el texto, contraste sobre el
PNG original (percentil 10 del fondo bajo cada texto) y faltas UB-3.

v2: cajas reales en Chrome con las fuentes de su paquete (Inter Variable).
v1: valores declarados en el SVG (su paquete no trae Bebas Neue ni Oswald, así
que renderizarla aquí sustituiría la fuente y falsearía las cajas).

Uso: python analisis/medir_piezas.py  ->  analisis/medidas_elegidas.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

import marca  # noqa: E402
from motor import Contexto, contrastes  # noqa: E402
from navegador import Navegador  # noqa: E402

PIEZAS = [
    {'pos': 'v1 1°', 'paquete': 'v1', 'archivo': '01_save-the-date_1080x1080_claro', 'codigo': '(sin código)'},
    {'pos': 'v2 1°', 'paquete': 'v2', 'archivo': '01_save-the-date_1080x1080_claro', 'codigo': 'STD-1080x1080-CLA'},
    {'pos': 'v2 12°', 'paquete': 'v2', 'archivo': '03_linkedin-portada_1200x627_oscuro', 'codigo': 'LI-OSC'},
    {'pos': 'v2 20°', 'paquete': 'v2', 'archivo': '02_taller-webinar_1080x1350_oscuro_mj-V-S17b', 'codigo': 'TAL-1350-OSC-V-S17b'},
    {'pos': 'v2 22°', 'paquete': 'v2', 'archivo': '03_carrusel-portada_1080x1350_oscuro_mj-V-S16b', 'codigo': 'CAR-OSC-V-S16b'},
    {'pos': 'v2 24°', 'paquete': 'v2', 'archivo': '05_slide-portada_1920x1080_oscuro_mj-V-S2b', 'codigo': 'SLC-OSC-V-S2b'},
]
VISTA_CELULAR = 390

JS = """
() => {
  const caja = el => { const b = el.getBBox(), m = el.getCTM();
    const p1 = new DOMPoint(b.x, b.y).matrixTransform(m), p2 = new DOMPoint(b.x + b.width, b.y + b.height).matrixTransform(m);
    return [p1.x, p1.y, p2.x - p1.x, p2.y - p1.y]; };
  const textos = [...document.querySelectorAll('text')].map(t => { const cs = getComputedStyle(t);
    return {id: t.id || null, texto: t.textContent, tam: parseFloat(cs.fontSize), familia: cs.fontFamily,
            peso: cs.fontWeight, relleno: t.getAttribute('fill'), caja: caja(t)}; });
  const grupos = {};
  for (const id of ['lockup', 'wireframe-iso', 'mj-plate', 'mj-fullbleed', 'example-banner', 'registration-marks', 'numbered-rows', 'logo-umbral', 'wordmark'])
    { const el = document.getElementById(id); if (el) grupos[id] = caja(el); }
  const bg = document.getElementById('bg');
  return {ancho: +document.documentElement.getAttribute('width'), alto: +document.documentElement.getAttribute('height'),
          fondo: bg ? bg.getAttribute('fill') : null, textos, grupos};
}
"""


def medir_v1(svg: Path) -> dict:
    """Valores declarados: x, y (línea base), font-size y clase de cada <text>."""
    crudo = svg.read_text(encoding='utf-8')
    w, h = (int(x) for x in re.search(r'width="(\d+)" height="(\d+)"', crudo).groups())
    fondo = re.search(r'<rect id="bg"[^>]*fill="([^"]+)"', crudo).group(1)
    clases = dict(re.findall(r'\.(\w[\w-]*)\s*\{[^}]*?font-family:\s*([^;]+);', crudo))
    textos = []
    for attrs, texto in re.findall(r'<text([^>]*)>([^<]*)</text>', crudo):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', attrs))
        tam = float(a.get('font-size', 0))
        textos.append({'id': a.get('id'), 'texto': texto, 'tam': tam, 'familia': clases.get(a.get('class', ''), '?'),
                       'relleno': a.get('fill'), 'x': float(a.get('x', 0)), 'y': float(a.get('y', 0)),
                       'caja': [float(a.get('x', 0)), float(a.get('y', 0)) - tam * 0.75, len(texto) * tam * 0.5, tam]})
    return {'ancho': w, 'alto': h, 'fondo': fondo, 'textos': textos, 'grupos': {},
            'familias_declaradas': sorted(set(re.findall(r"font-family:\s*'([^']+)'", crudo))),
            'dominios': sorted(set(re.findall(r'umbralbim\.[a-z]+', crudo))),
            'wordmark_texto': bool(re.search(r'id="wordmark"', crudo)),
            'banda_ejemplo_ancho_completo': bool(re.search(r'<rect[^>]*id="example-banner"|id="example-banner"', crudo))}


def contraste_p10(png: Image.Image, caja, escala: float, relleno: str) -> float | None:
    x, y, w, h = (v * escala for v in caja)
    x0, y0 = max(0, int(x)), max(0, int(y))
    x1, y1 = min(png.width, int(x + w) + 1), min(png.height, int(y + h) + 1)
    if x1 <= x0 or y1 <= y0 or not relleno or not relleno.startswith('#'):
        return None
    px = np.asarray(png.crop((x0, y0, x1, y1)), dtype=float).reshape(-1, 3)
    rgb = marca.color_rgba(relleno)[:3]
    # el fondo bajo el texto: se descartan los píxeles del propio texto (cercanos a su color)
    dist = np.abs(px - np.array(rgb)).sum(axis=1)
    fondo = px[dist > 60] if (dist > 60).sum() > 20 else px
    return round(float(np.percentile(contrastes(rgb, fondo), 10)), 2)


def mayor_vacio_vertical(cajas: list, alto: float, x_max: float) -> tuple[float, float]:
    """Banda horizontal vacía más alta en la columna izquierda (x < x_max)."""
    ocupado = sorted((c[1], c[1] + c[3]) for c in cajas if c[0] < x_max and c[3] > 0)
    mejor, desde, y = (0.0, 0.0), 0.0, 0.0
    for a, b in ocupado:
        if a - y > mejor[0]:
            mejor = (a - y, y)
        y = max(y, b)
    return round(mejor[0], 1), round(mejor[1], 1)


def analizar(ctx: Contexto, p: dict, datos: dict, png: Image.Image) -> dict:
    W, H = datos['ancho'], datos['alto']
    escala = png.width / W
    tokens = {v.upper(): f'{k} ({tema})' for tema in ('claro', 'oscuro') for k, v in ctx.tokens[tema].items()
              if isinstance(v, str) and v.startswith('#')}
    fondo = (datos['fondo'] or '').upper()
    textos = datos['textos']
    tam_titulo = max((t['tam'] for t in textos if (t['id'] or '').startswith('title')), default=None)
    filas = [t for t in textos if (t['id'] or '').startswith('row-value')]
    etiquetas = [t for t in textos if (t['id'] or '').startswith('row-label')]
    vista = 1280 if W == 1920 else VISTA_CELULAR
    css = lambda px: round(px * vista / W, 1)
    css_cel = lambda px: round(px * VISTA_CELULAR / W, 1)
    claro = marca.luminancia(marca.color_rgba(fondo)[:3]) > 0.4 if fondo.startswith('#') else False
    turq = ctx.tokens['claro']['--ub-primary'].upper()
    turquesa_sobre_claro = [t['id'] for t in textos if (t['relleno'] or '').upper() == turq and claro]
    # la imagen a sangre cubre todo el lienzo: no cuenta como contenido para medir vacíos
    cajas = [t['caja'] for t in textos] + [c for k, c in datos['grupos'].items()
                                           if k not in ('registration-marks', 'mj-fullbleed')]
    vacio, vacio_desde = mayor_vacio_vertical(cajas, H, W * 0.5)
    izquierda = min((t['caja'][0] for t in textos), default=None)
    res = {
        'pieza': p['pos'], 'codigo': p['codigo'], 'archivo': p['archivo'], 'formato': f'{W}x{H}',
        'fondo': fondo, 'fondo_token': tokens.get(fondo, 'no es token'),
        'tamanos_px': sorted({round(t['tam'], 1) for t in textos}),
        'n_tamanos_distintos': len({round(t['tam'], 1) for t in textos}),
        'titulo_px': tam_titulo,
        'titulo_mayuscula_rel_alto': round(tam_titulo * 0.727 / H, 4) if tam_titulo else None,
        'valor_fila_px': filas[0]['tam'] if filas else None,
        'valor_fila_css': css(filas[0]['tam']) if filas else None,
        'etiqueta_fila_px': etiquetas[0]['tam'] if etiquetas else None,
        'etiqueta_fila_css': css(etiquetas[0]['tam']) if etiquetas else None,
        'texto_minimo_px': min(t['tam'] for t in textos if t['texto'].strip()),
        'texto_minimo_css': css(min(t['tam'] for t in textos if t['texto'].strip())),
        'texto_minimo_css_celular': css_cel(min(t['tam'] for t in textos if t['texto'].strip())),
        'vista_css': vista,
        'margen_izquierdo_px': round(izquierda, 1) if izquierda is not None else None,
        'mayor_vacio_columna_izq_px': vacio, 'mayor_vacio_desde_y': vacio_desde,
        'mayor_vacio_rel_alto': round(vacio / H, 3),
        'turquesa_texto_sobre_claro': turquesa_sobre_claro,
        'grupos': {k: [round(x, 1) for x in v] for k, v in datos['grupos'].items()},
    }
    # contraste: sobre imagen, percentil 10 del PNG original bajo el texto; sobre fondo
    # plano, color contra color (la trama de puntos no cuenta como fondo, igual que en el motor)
    imagenes = [v for k, v in datos['grupos'].items() if k in ('mj-plate', 'mj-fullbleed')]
    toca = lambda c, r: not (c[0] + c[2] <= r[0] or r[0] + r[2] <= c[0] or c[1] + c[3] <= r[1] or r[1] + r[3] <= c[1])
    cr = {}
    for t in textos:
        if not (t['texto'].strip() and t['id'] and (t['relleno'] or '').startswith('#')):
            continue
        if any(toca(t['caja'], r) for r in imagenes):
            c = contraste_p10(png, t['caja'], escala, t['relleno'])
        elif t['id'] == 'example-banner' or (t['id'] or '').startswith('example'):
            continue
        else:
            c = round(marca.contraste(marca.color_rgba(t['relleno'])[:3], marca.color_rgba(fondo)[:3]), 2)
        if c is not None:
            cr[t['id']] = c
    res['contraste_p10'] = cr
    res['contraste_minimo'] = min(cr.items(), key=lambda kv: kv[1]) if cr else None
    res['textos_bajo_4_5'] = sorted(k for k, v in cr.items() if v < 4.5)
    g = datos['grupos']
    if 'lockup' in g:
        res['lockup_ancho_px'] = round(g['lockup'][2], 1)
        res['margen_inferior_px'] = round(H - (g['lockup'][1] + g['lockup'][3]), 1)
    if 'example-banner' in g and 'registration-marks' in g:
        chip = g['example-banner']
        x2 = chip[0] + chip[2]
        res['chip_toca_cruz_registro'] = bool(x2 > W - 32 - 9 and chip[1] < 32 + 9)
    iso = g.get('wireframe-iso')
    if iso:
        referencia = [t['caja'] for t in textos] + [v for k, v in g.items() if k in ('numbered-rows', 'lockup')]
        bordes_texto = sorted({round(c[1], 1) for c in referencia} | {round(c[1] + c[3], 1) for c in referencia})
        cerca = lambda y: min(abs(y - b) for b in bordes_texto)
        res['isometria'] = {'caja': [round(v, 1) for v in iso],
                            'distancia_borde_sup_a_linea_de_texto_px': round(cerca(iso[1]), 1),
                            'distancia_borde_inf_a_linea_de_texto_px': round(cerca(iso[1] + iso[3]), 1),
                            'distancia_a_margen_derecho_px': round(W - (iso[0] + iso[2]), 1)}
    placa = g.get('mj-plate')
    if placa:
        filas_top = min((t['caja'][1] for t in filas), default=None)
        res['imagen_caja'] = {'caja': [round(v, 1) for v in placa],
                              'margen_derecho_px': round(W - (placa[0] + placa[2]), 1),
                              'tope_vs_primera_fila_px': round(placa[1] - filas_top, 1) if filas_top else None,
                              'ocupa_ancho_rel': round(placa[2] / W, 3), 'ocupa_alto_rel': round(placa[3] / H, 3)}
    return res


def main():
    ctx = Contexto()
    raices = {'v2': (LAB / ctx.rutas['v2_paquete']).resolve(), 'v1': (LAB / ctx.rutas['v1_paquete']).resolve()}
    salida = []
    with Navegador(raices, ctx.rutas['navegador']['canal']) as nav:
        for p in PIEZAS:
            raiz = raices[p['paquete']]
            png = Image.open(raiz / 'png' / f"{p['archivo']}.png").convert('RGB')
            if p['paquete'] == 'v1':
                datos = medir_v1(raiz / 'svg' / f"{p['archivo']}.svg")
            else:
                url = nav.url('v2', f"svg/{p['archivo']}.svg")
                m = re.search(r'_(\d+)x(\d+)_', p['archivo'])
                datos = nav.evaluar(url, int(m.group(1)), int(m.group(2)), JS)
            res = analizar(ctx, p, datos, png)
            if p['paquete'] == 'v1':
                res.update({k: datos[k] for k in ('familias_declaradas', 'dominios', 'wordmark_texto')})
            salida.append(res)
            print(f"{p['pos']:7s} titulo {res['titulo_px']} px · valor {res['valor_fila_css']} css · "
                  f"min {res['texto_minimo_css_celular']} css(cel) · tamaños {res['n_tamanos_distintos']} · "
                  f"vacío {res['mayor_vacio_rel_alto']} · contraste mín {res['contraste_minimo']} · "
                  f"turq/claro {res['turquesa_texto_sobre_claro']}")
    (LAB / 'analisis' / 'medidas_elegidas.json').write_text(
        json.dumps(salida, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
