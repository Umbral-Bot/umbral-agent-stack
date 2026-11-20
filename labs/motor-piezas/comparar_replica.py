#!/usr/bin/env python3
"""Compara una pieza regenerada por el motor con su original de la v2.

Renderiza el SVG original en el mismo Chrome (para no confundir diferencias de
rasterizador con diferencias de composición) y mide:
  - posición y tamaño de cada elemento mapeado (getBBox, en px del lienzo);
  - diferencia de píxeles (media absoluta 0-255 y % de píxeles con delta > 16).
Escribe <salida>/piezas/<codigo>.comparacion.json y una lámina original | réplica | diferencia.

Uso: python comparar_replica.py --pack packs/R1-replica-v2-01.yaml --salida salida/prueba [--codigo R1]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))

from motor import Contexto, cargar_yaml  # noqa: E402
from navegador import Navegador  # noqa: E402

JS_CAJAS = """
(ids) => Object.fromEntries(ids.map(id => {
  const el = document.getElementById(id);
  if (!el) return [id, null];
  const b = el.getBBox();
  const m = el.getCTM();
  // caja en coordenadas del lienzo (aplica la transformación del elemento)
  const p1 = new DOMPoint(b.x, b.y).matrixTransform(m), p2 = new DOMPoint(b.x + b.width, b.y + b.height).matrixTransform(m);
  return [id, [p1.x, p1.y, p2.x - p1.x, p2.y - p1.y].map(v => Math.round(v * 10) / 10)];
}))
"""


def comparar(ctx: Contexto, ruta_pack: Path, dir_salida: Path, codigo: str) -> dict:
    pack = cargar_yaml(ruta_pack)
    ctrl = pack['control']
    v2 = (LAB / ctx.rutas['v2_paquete']).resolve()
    info = json.loads((dir_salida / 'piezas' / f'{codigo}.json').read_text(encoding='utf-8'))
    W, H = info['ancho'], info['alto']
    escala = ctx.rutas['navegador']['escala_png']
    with Navegador({'v2': v2, 'salida': dir_salida.resolve()}, ctx.rutas['navegador']['canal']) as nav:
        png_orig = dir_salida / 'png' / f'{codigo}.original.png'
        nav.rasterizar(nav.url('v2', ctrl['original_svg']), W, H, escala, png_orig)
        cajas_o = nav.evaluar(nav.url('v2', ctrl['original_svg']), W, H, JS_CAJAS, list(ctrl['mapa_ids']))
        cajas_r = nav.evaluar(nav.url('salida', info['svg']), W, H, JS_CAJAS, list(ctrl['mapa_ids'].values()))
    deltas = {}
    for id_o, id_r in ctrl['mapa_ids'].items():
        a, b = cajas_o.get(id_o), cajas_r.get(id_r)
        if a is None or b is None:
            deltas[id_o] = {'falta': 'original' if a is None else 'réplica'}
            continue
        deltas[id_o] = {'dx': round(b[0] - a[0], 1), 'dy': round(b[1] - a[1], 1),
                        'dw': round(b[2] - a[2], 1), 'dh': round(b[3] - a[3], 1)}
    maximo = max((max(abs(d[k]) for k in ('dx', 'dy', 'dw', 'dh')) for d in deltas.values() if 'dx' in d), default=None)
    a = Image.open(png_orig).convert('RGB')
    b = Image.open(dir_salida / info['png']).convert('RGB')
    dif = ImageChops.difference(a, b).convert('L')
    arr = np.asarray(dif, dtype=float)
    res = {'codigo': codigo, 'original': ctrl['original_svg'], 'cajas_original': cajas_o, 'cajas_replica': cajas_r,
           'deltas_px': deltas, 'delta_max_px': maximo,
           'pixeles': {'media_abs_0_255': round(float(arr.mean()), 3),
                       'pct_delta_mayor_16': round(float((arr > 16).mean() * 100), 3)}}
    (dir_salida / 'piezas' / f'{codigo}.comparacion.json').write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
    # lámina original | réplica | diferencia (amplificada)
    t = 720
    ims = [a.resize((t, t * a.height // a.width)), b.resize((t, t * b.height // b.width)),
           Image.eval(dif, lambda p: min(255, p * 4)).convert('RGB').resize((t, t * a.height // a.width))]
    fondo = ctx.tokens['claro']['--ub-bg']
    tinta = ctx.tokens['claro']['--ub-text']
    lam = Image.new('RGB', (3 * t + 4 * 24, ims[0].height + 80), fondo)
    d = ImageDraw.Draw(lam)
    fuente = ImageFont.truetype(str(ctx.marca / ctx.rutas['insumos_director'] / '02_fuentes' / 'Inter-Variable.ttf'), 22)
    fuente.set_variation_by_axes([14, 500])   # corte de texto (opsz 14), peso 500
    for i, (im, rot) in enumerate(zip(ims, ('Original v2 (Chrome)', 'Réplica desde pack', 'Diferencia ×4'))):
        x = 24 + i * (t + 24)
        lam.paste(im, (x, 64))
        d.text((x, 24), rot, fill=tinta, font=fuente)
    lam.save(dir_salida / 'png' / f'{codigo}.comparacion.png')
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pack', required=True)
    ap.add_argument('--salida', required=True)
    ap.add_argument('--codigo')
    a = ap.parse_args()
    ruta_pack = Path(a.pack)
    codigo = a.codigo or cargar_yaml(ruta_pack)['id']
    res = comparar(Contexto(), ruta_pack, LAB / a.salida, codigo)
    print(json.dumps({k: res[k] for k in ('delta_max_px', 'pixeles', 'deltas_px')}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
