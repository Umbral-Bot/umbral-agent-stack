#!/usr/bin/env python3
"""Galería numerada (1°, 2°…) de piezas del motor, cada una con su pack visible.

Genera todas las piezas de una definición (galerias/*.yaml), el control de
réplica, una hoja 00_preview.jpg numerada y galeria.html. Con --publicar copia
la carpeta a 07_Motor de piezas/01_galerias/ en Drive (nunca a 00_insumos).

Uso: python galeria.py --definicion galerias/G01.yaml [--publicar]
"""
from __future__ import annotations

import argparse
import base64
import csv
import html
import io
import json
import math
import shutil
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))

from motor import Contexto, abrir_navegador, cargar_pack, cargar_yaml, generar_pieza  # noqa: E402
from comparar_replica import comparar  # noqa: E402


def copiar_pack(ruta_pack: str, destino: Path):
    """Copia el pack y los packs de los que hereda, para que la carpeta publicada se explique sola."""
    ruta = LAB / ruta_pack
    while ruta is not None:
        shutil.copy2(ruta, destino / ruta.name)
        padre = cargar_yaml(ruta).get('hereda')
        ruta = LAB / padre if padre else None


def previsualizar(info: dict, dir_salida: Path, ancho: int) -> str:
    im = Image.open(dir_salida / info['png']).convert('RGB')
    alto = round(im.height * ancho / im.width)
    destino = dir_salida / 'prev' / f"{info['codigo']}.jpg"
    destino.parent.mkdir(exist_ok=True)
    im.resize((ancho, alto), Image.Resampling.LANCZOS).save(destino, quality=88, optimize=True)
    return f"prev/{info['codigo']}.jpg"


def hoja_numerada(items: list[dict], dir_salida: Path, titulo: str, fuente_ttf: Path, colores: dict) -> Path:
    """Hoja de contacto como la 00_preview.jpg de la v2: número de posición grande + código.

    Si todas las piezas son apaisadas (16:9, LinkedIn), van de a dos por fila y más grandes."""
    apaisadas = all(it['ancho'] / it['alto'] >= 1.5 for it in items)
    cols, celda, celda_h = (2, 860, 484) if apaisadas else (4, 420, 420)
    pad, rotulo, cab = 28, 64, 88
    filas = math.ceil(len(items) / cols)
    hoja = Image.new('RGB', (cols * celda + (cols + 1) * pad, cab + filas * (celda_h + rotulo) + (filas + 1) * pad),
                     colores['fondo'])
    d = ImageDraw.Draw(hoja)

    def f(tam, peso):
        fnt = ImageFont.truetype(str(fuente_ttf), tam)
        try:
            fnt.set_variation_by_axes([14, peso])   # opsz 14 (corte de texto, como las woff2 canónicas)
        except Exception:
            pass
        return fnt

    d.text((pad, 28), titulo, fill=colores['acento_texto'], font=f(28, 600))
    for i, it in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (celda + pad)
        y = cab + pad + r * (celda_h + rotulo + pad)
        im = Image.open(dir_salida / it['png']).convert('RGB')
        im.thumbnail((celda, celda_h), Image.Resampling.LANCZOS)
        d.rectangle([x - 1, y - 1, x + celda, y + celda_h], outline=colores['filete'], width=1)
        hoja.paste(im, (x + (celda - im.width) // 2, y + (celda_h - im.height) // 2))
        d.text((x, y + celda_h + 8), it['numero'], fill=colores['tinta'], font=f(36, 600))
        d.text((x + 76, y + celda_h + 12), it['codigo'], fill=colores['acento_texto'], font=f(15, 500))
        d.text((x + 76, y + celda_h + 34), it['rotulo'][:54 if not apaisadas else 110], fill=colores['secundario'],
               font=f(13, 500))
    destino = dir_salida / '00_preview.jpg'
    hoja.save(destino, quality=90, optimize=True)
    return destino


def hoja_detalle(items: list[dict], dir_salida: Path, detalle: dict, fuente_ttf: Path, colores: dict,
                 escala_png: float) -> Path:
    """Recorte de la misma zona de cada pieza, lado a lado y numerado: para pasos que cambian algo
    chico (por ejemplo, colores del texto) que en la hoja completa casi no se ve."""
    x0, y0, x1, y1 = detalle['recorte']          # px del lienzo
    ancho = 420
    alto = round(ancho * (y1 - y0) / (x1 - x0))
    pad, rotulo, cab = 28, 64, 88
    hoja = Image.new('RGB', (len(items) * ancho + (len(items) + 1) * pad, cab + alto + rotulo + 2 * pad),
                     colores['fondo'])
    d = ImageDraw.Draw(hoja)

    def f(tam, peso):
        fnt = ImageFont.truetype(str(fuente_ttf), tam)
        try:
            fnt.set_variation_by_axes([14, peso])
        except Exception:
            pass
        return fnt

    d.text((pad, 28), detalle['titulo'], fill=colores['acento_texto'], font=f(28, 600))
    for i, it in enumerate(items):
        x, y = pad + i * (ancho + pad), cab + pad
        im = Image.open(dir_salida / it['png']).convert('RGB')
        k = escala_png
        im = im.crop((round(x0 * k), round(y0 * k), round(x1 * k), round(y1 * k)))
        hoja.paste(im.resize((ancho, alto), Image.Resampling.LANCZOS), (x, y))
        d.rectangle([x - 1, y - 1, x + ancho, y + alto], outline=colores['filete'], width=1)
        d.text((x, y + alto + 8), it['numero'], fill=colores['tinta'], font=f(36, 600))
        d.text((x + 76, y + alto + 12), it['codigo'], fill=colores['acento_texto'], font=f(15, 500))
    destino = dir_salida / '01_detalle.jpg'
    hoja.save(destino, quality=90, optimize=True)
    return destino


def construir(ruta_def: Path, publicar: bool):
    ctx = Contexto()
    defin = cargar_yaml(ruta_def)
    gid = defin['id']
    dir_salida = LAB / 'salida' / gid
    if dir_salida.exists():
        shutil.rmtree(dir_salida)
    dir_salida.mkdir(parents=True)
    (dir_salida / 'packs').mkdir()
    contenido_def = defin['contenido']
    items, numero = [], 0
    with abrir_navegador(ctx) as nav:
        nav.preparar_medicion(ctx.css_fuentes(nav.url('fuentes', '')))
        for sec in defin['secciones']:
            for ruta_pack in sec['piezas']:
                numero += 1
                pack = cargar_pack(LAB / ruta_pack)
                # una sección puede probar los mismos packs con otro contenido (sufijo en el código)
                codigo = f"{gid}-{pack['id']}" + (f"-{sec['sufijo']}" if sec.get('sufijo') else '')
                info = generar_pieza(ctx, nav, LAB / ruta_pack, dir_salida, codigo,
                                     LAB / (sec.get('contenido') or pack.get('contenido', contenido_def)),
                                     sec.get('valores'))
                copiar_pack(ruta_pack, dir_salida / 'packs')
                info.update({'numero': f'{numero}°', 'seccion': sec['alternativa'],
                             'rotulo': f"{pack['nombre']}", 'pack_yaml': (LAB / ruta_pack).read_text(encoding='utf-8'),
                             'prev': previsualizar(info, dir_salida, 780 if info['formato'] != 'slide' else 1280)})
                items.append(info)
                print(f"{info['numero']:>4} {codigo:10s} {info['estado']:12s} {info['formato']}/{info['modo']}  "
                      f"{'; '.join(info['reglas_rotas']) or '-'}")
        controles = []
        for c in defin.get('control', []):
            pack = cargar_pack(LAB / c['pack'])
            codigo = f"{gid}-{pack['id']}"
            info = generar_pieza(ctx, nav, LAB / c['pack'], dir_salida, codigo, LAB / pack['contenido'])
            copiar_pack(c['pack'], dir_salida / 'packs')
            info.update({'rotulo': pack['nombre'], 'pack_yaml': (LAB / c['pack']).read_text(encoding='utf-8'),
                         'prev': previsualizar(info, dir_salida, 780)})
            controles.append(info)
    for info in controles:
        info['comparacion'] = comparar(ctx, LAB / next(c['pack'] for c in defin['control']
                                                       if cargar_pack(LAB / c['pack'])['id'] == info['pack']),
                                       dir_salida, info['codigo'])
        print(f"control {info['codigo']}: delta máx {info['comparacion']['delta_max_px']} px, "
              f"píxeles {info['comparacion']['pixeles']}")
    colores = {k: ctx.tokens['claro'][t] for k, t in
               {'fondo': '--ub-bg', 'tinta': '--ub-text', 'secundario': '--ub-text-muted',
                'acento_texto': '--ub-primary-text', 'filete': '--ub-border'}.items()}
    ttf = ctx.marca / ctx.rutas['insumos_director'] / '02_fuentes' / 'Inter-Variable.ttf'
    hoja_numerada(items, dir_salida, f"UMBRAL BIM  ·  MOTOR DE PIEZAS  ·  {gid}  ·  LABORATORIO", ttf, colores)
    if defin.get('detalle'):
        # el detalle puede limitarse a algunas secciones (las que cambian algo chico)
        secs = defin['detalle'].get('secciones')
        en_detalle = [it for it in items if not secs or it['seccion'] in secs]
        hoja_detalle(en_detalle, dir_salida, defin['detalle'], ttf, colores, ctx.rutas['navegador']['escala_png'])
    (dir_salida / 'galeria.html').write_text(html_galeria(defin, items, controles, ctx), encoding='utf-8')
    (dir_salida / 'alternativas.html').write_text(html_autocontenido(defin, items, dir_salida, ctx), encoding='utf-8')
    with open(dir_salida / f'decisiones_{gid}.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['numero', 'codigo', 'pack', 'comentario_david', 'fecha'])
        for it in items:
            w.writerow([it['numero'], it['codigo'], it['pack_archivo'], '', ''])
    (dir_salida / 'galeria.json').write_text(json.dumps(
        {'id': gid, 'piezas': [{k: it[k] for k in ('numero', 'codigo', 'pack', 'pack_archivo', 'estado',
                                                  'reglas_rotas', 'formato', 'modo', 'png')} for it in items],
         'controles': [{'codigo': c['codigo'], 'estado': c['estado'], 'comparacion': c['comparacion']}
                       for c in controles]}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'galería: {dir_salida / "galeria.html"}')
    if publicar:
        destino = ctx.marca / ctx.rutas['galerias_drive'] / f"{defin['fecha']}_{gid}"
        if (ctx.rutas['insumos_director'] in str(destino)):
            raise RuntimeError('destino dentro de 00_insumos: prohibido')
        if destino.exists():
            shutil.rmtree(destino)
        shutil.copytree(dir_salida, destino)
        print(f'publicada en: {destino}')


# -----------------------------------------------------------------------------
# HTML
# -----------------------------------------------------------------------------

def _e(x) -> str:
    return html.escape(str(x))


def tarjeta(it: dict, vista: int) -> str:
    d = it['derivados']
    ver = {x['regla']: x for x in it['verificaciones']}
    rotas = [x for x in it['verificaciones'] if not x['ok']]
    estado_cls = 'ok' if it['estado'] == 'cumple UB-3' else 'exp'
    contrastes = d.get('contrastes') or {}
    peor = min(contrastes.items(), key=lambda kv: kv[1]) if contrastes else None
    imagen = it.get('imagen')
    filas_ver = ''.join(
        f"<li class='{'ok' if x['ok'] else 'no'}'><b>{_e(x['regla'])}</b> {_e(x['detalle'])}"
        f"{' <i>(calidad)</i>' if x['clase'] == 'calidad' else ''}</li>" for x in it['verificaciones'])
    notas = ''.join(f'<li>{_e(n)}</li>' for n in it['notas']) or '<li>sin ajustes automáticos</li>'
    img_html = ''
    if imagen:
        img_html = (f"<p class='meta'><b>Imagen:</b> {_e(imagen['archivo'])} · {_e(imagen['herramienta'])} "
                    f"{_e(imagen['modelo'])} · {_e(imagen['parametros'])} · encaje {_e(imagen['encaje'])} · "
                    f"<b>imagen fija, no reproducible</b> (sin --sref ni semilla)<br>"
                    f"<span class='prompt'>«{_e(imagen['prompt'])}»</span></p>")
    return f"""
<article class="pieza" id="p{_e(it['numero'].rstrip('°'))}">
  <header><span class="num">{_e(it['numero'])}</span>
    <span class="cod">{_e(it['codigo'])}</span>
    <span class="estado {estado_cls}">{_e(it['estado'])}</span></header>
  <p class="rot">{_e(it['rotulo'])} · {_e(it['formato'])} {it['ancho']}×{it['alto']} · {_e(it['modo'])}</p>
  <a href="{_e(it['png'])}" target="_blank"><img src="{_e(it['prev'])}" style="width:{vista}px" alt="{_e(it['codigo'])}"></a>
  <p class="meta">Vista a {vista} px CSS{' (celular)' if vista == 390 else ''} · <a href="{_e(it['png'])}">PNG 2×</a> ·
    <a href="{_e(it['svg'])}">SVG</a> · <a href="packs/{_e(Path(it['pack_archivo']).name)}">pack</a></p>
  <p class="meta"><b>Medidas:</b> texto mínimo {d['tamanos_css']['etiqueta']} px CSS · valor {d['tamanos_css']['valor']} px CSS ·
    título {d['titulo_px']} px · margen {d['margen']} · medianil {d['medianil']} · módulo {d['modulo']} ·
    contraste más bajo {f"{peor[1]}:1 ({_e(peor[0])})" if peor else '-'}</p>
  {img_html}
  <details{' open' if rotas else ''}><summary>Verificación UB-3 y calidad ({len(rotas)} observaciones)</summary><ul class="ver">{filas_ver}</ul></details>
  <details><summary>Ajustes que hizo el motor</summary><ul>{notas}</ul></details>
  <p class="meta"><b>Pack</b> <code>{_e(it['pack_archivo'])}</code></p>
  <pre class="pack">{_e(it['pack_yaml'])}</pre>
</article>"""


def html_autocontenido(defin: dict, items: list[dict], dir_salida: Path, ctx: Contexto) -> str:
    """Página de un solo archivo, con las imágenes embebidas, para comparar las alternativas en el
    celular o mandarla por chat. Sin packs ni verificaciones: eso queda en galeria.html."""
    t = ctx.tokens['claro']

    def img(it: dict, ancho: int = 1080) -> str:
        im = Image.open(dir_salida / it['png']).convert('RGB')
        im = im.resize((ancho, round(im.height * ancho / im.width)), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=84, optimize=True, progressive=True)
        return base64.b64encode(buf.getvalue()).decode('ascii')

    secciones = []
    for sec in defin['secciones']:
        propias = [it for it in items if it['seccion'] == sec['alternativa']]
        tarjetas = []
        for i, it in enumerate(propias):
            desc = sec['pasos'][i] if i < len(sec.get('pasos', [])) else it['rotulo']
            nombre, _, detalle = desc.partition(': ')
            tarjetas.append(f"""
      <article class="alt">
        <div class="cab"><span class="num">{_e(it['numero'])}</span><span class="nom">{_e(nombre)}</span></div>
        <p class="det">{_e(detalle)}</p>
        <img src="data:image/jpeg;base64,{img(it)}" alt="{_e(it['codigo'])}" loading="lazy">
        <p class="cod">{_e(it['codigo'])} · {it['ancho']}×{it['alto']} · {_e(it['estado'])}</p>
      </article>""")
        secciones.append(f"""
    <section>
      <h2>{_e(sec['titulo'])}</h2>
      <p class="sub">{_e(sec.get('descripcion', '').strip())}</p>
      <div class="rejilla">{''.join(tarjetas)}</div>
    </section>""")
    intro = defin.get('resumen') or defin['descripcion']
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(defin['titulo'])}</title>
<style>
:root {{ --bg:{t['--ub-bg']}; --sup:{t['--ub-surface']}; --tx:{t['--ub-text']}; --mu:{t['--ub-text-muted']};
        --bo:{t['--ub-border']}; --pt:{t['--ub-primary-text']}; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--tx);
       font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; line-height:1.5; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 24px 16px 56px; }}
.kicker {{ color:var(--pt); font-weight:600; letter-spacing:.12em; text-transform:uppercase; font-size:12px; margin:0; }}
h1 {{ font-size: 26px; line-height:1.2; margin: 6px 0 8px; font-weight:600; letter-spacing:-.3px; }}
.intro {{ color:var(--mu); margin:0 0 8px; max-width: 760px; }}
.pide {{ background:var(--sup); border:1px solid var(--bo); border-radius:8px; padding:12px 14px; margin:16px 0 8px; }}
h2 {{ font-size: 20px; margin: 32px 0 2px; font-weight:600; }}
.sub {{ color:var(--mu); margin:0 0 12px; font-size:14px; }}
.rejilla {{ display:grid; grid-template-columns: 1fr; gap: 16px; }}
@media (min-width: 760px) {{ .rejilla {{ grid-template-columns: 1fr 1fr; }} }}
.alt {{ background:var(--sup); border:1px solid var(--bo); border-radius:8px; padding:12px; }}
.cab {{ display:flex; align-items:baseline; gap:10px; }}
.num {{ font-size: 34px; font-weight:600; letter-spacing:-1px; }}
.nom {{ font-size: 18px; font-weight:600; }}
.det {{ color:var(--mu); margin: 2px 0 10px; font-size:14px; }}
img {{ display:block; width:100%; height:auto; border:1px solid var(--bo); border-radius:4px; }}
.cod {{ color:var(--mu); font-size:12px; margin:8px 0 0; font-family: "JetBrains Mono", ui-monospace, monospace; }}
.pie {{ color:var(--mu); font-size:12px; margin-top:32px; }}
</style></head>
<body><main>
  <p class="kicker">Umbral BIM · laboratorio motor de piezas · {_e(str(defin['fecha']))}</p>
  <h1>{_e(defin['titulo'])}</h1>
  <p class="intro">{_e(intro.strip())}</p>
  <p class="pide">{_e(defin['como_elegir'].strip())}</p>
  {''.join(secciones)}
  <p class="pie">Piezas de ejemplo (fecha ficticia): no publicar. Packs, medidas y verificación UB-3 en galeria.html.</p>
</main></body></html>
"""


def html_galeria(defin: dict, items: list[dict], controles: list[dict], ctx: Contexto) -> str:
    t = ctx.tokens['claro']
    secciones = []
    for sec in defin['secciones']:
        tarjetas = ''.join(tarjeta(it, 640 if it['formato'] == 'slide' else 390)
                           for it in items if it['seccion'] == sec['alternativa'])
        pasos = ''.join(f'<li>{_e(p)}</li>' for p in sec.get('pasos', []))
        secciones.append(f"""
<section><h2>{_e(sec['titulo'])}</h2><p class="desc">{_e(sec['descripcion'])}</p>
<ol class="pasos">{pasos}</ol><div class="rejilla">{tarjetas}</div></section>""")
    ctrl = ''
    for c in controles:
        cmp_ = c['comparacion']
        filas = ''.join(f"<tr><td>{_e(k)}</td><td>{_e(v.get('dx', '-'))}</td><td>{_e(v.get('dy', '-'))}</td>"
                        f"<td>{_e(v.get('dw', '-'))}</td><td>{_e(v.get('dh', '-'))}</td></tr>"
                        for k, v in cmp_['deltas_px'].items())
        ctrl += f"""
<article class="control"><header><span class="cod">{_e(c['codigo'])}</span>
<span class="estado {'ok' if c['estado'] == 'cumple UB-3' else 'exp'}">{_e(c['estado'])}</span></header>
<p class="rot">{_e(c['rotulo'])}</p>
<img src="png/{_e(c['codigo'])}.comparacion.png" style="width:100%">
<p class="meta">Diferencia de píxeles: media {cmp_['pixeles']['media_abs_0_255']}/255 · {cmp_['pixeles']['pct_delta_mayor_16']} % de píxeles con delta &gt; 16 ·
desplazamiento máximo de una caja {cmp_['delta_max_px']} px.</p>
<p class="meta">{_e(defin.get('nota_control', ''))}</p>
<details><summary>Cajas elemento a elemento (px, réplica − original)</summary>
<table><tr><th>elemento v2</th><th>dx</th><th>dy</th><th>dw</th><th>dh</th></tr>{filas}</table></details>
<details><summary>Verificación</summary><ul class="ver">{''.join(f"<li class='{'ok' if x['ok'] else 'no'}'><b>{_e(x['regla'])}</b> {_e(x['detalle'])}</li>" for x in c['verificaciones'])}</ul></details>
<pre class="pack">{_e(c['pack_yaml'])}</pre></article>"""
    fuentes = ctx.css_fuentes('fuentes/')
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(defin['titulo'])}</title>
<style>{fuentes}
:root{{--bg:{t['--ub-bg']};--sub:{t['--ub-bg-subtle']};--sup:{t['--ub-surface']};--tx:{t['--ub-text']};--mu:{t['--ub-text-muted']};
--bo:{t['--ub-border']};--pt:{t['--ub-primary-text']};--ok:{t['--ub-success-text']};--oks:{t['--ub-success-soft']};
--ws:{t['--ub-warning-soft']};--wt:{t['--ub-warning-text']}}}
body{{margin:0;background:var(--bg);color:var(--tx);font-family:'Inter',system-ui,sans-serif;font-feature-settings:"cv11","ss01","ss03";line-height:1.5}}
main{{max-width:1760px;margin:0 auto;padding:40px 32px 80px}}
h1{{font-weight:600;font-size:32px;letter-spacing:-0.5px;margin:0 0 4px}} h2{{font-weight:600;font-size:24px;margin:48px 0 4px}}
.kicker{{color:var(--pt);font-weight:600;letter-spacing:.12em;text-transform:uppercase;font-size:12px}}
.desc{{color:var(--mu);max-width:980px;margin:4px 0 8px}} .pasos{{color:var(--mu);font-size:14px;max-width:980px}}
.rejilla{{display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start}}
.pieza,.control{{background:var(--sup);border:1px solid var(--bo);border-radius:8px;padding:16px;box-sizing:border-box}}
.pieza{{width:680px}} .control{{max-width:1180px}}
.indice td,.indice th{{text-align:left}} .indice a{{text-decoration:none}}
.pieza header,.control header{{display:flex;gap:12px;align-items:baseline}}
.num{{font-size:40px;font-weight:600;letter-spacing:-1px}} .cod{{font-family:'JetBrains Mono',monospace;color:var(--pt);font-size:14px}}
.estado{{font-size:12px;font-weight:600;padding:2px 8px;border-radius:4px;margin-left:auto}}
.estado.ok{{background:var(--oks);color:var(--ok)}} .estado.exp{{background:var(--ws);color:var(--wt)}}
.rot{{margin:4px 0 8px;font-weight:500}} img{{display:block;border:1px solid var(--bo);height:auto;max-width:100%}}
.meta{{font-size:13px;color:var(--mu);margin:8px 0}} .prompt{{font-family:'JetBrains Mono',monospace;font-size:12px}}
.pack{{font-family:'JetBrains Mono',monospace;font-size:11.5px;background:var(--sub);border:1px solid var(--bo);border-radius:4px;padding:12px;max-height:360px;overflow:auto;white-space:pre}}
details{{font-size:13px;margin:6px 0}} summary{{cursor:pointer;color:var(--pt);font-weight:500}}
.ver li.no{{color:var(--wt)}} .ver li.ok{{color:var(--mu)}} table{{font-size:12px;border-collapse:collapse}} td,th{{border:1px solid var(--bo);padding:2px 8px;text-align:right}}
.aviso{{background:var(--ws);color:var(--wt);border-radius:8px;padding:12px 16px;max-width:980px}}
a{{color:var(--pt)}}
</style></head><body><main>
<p class="kicker">Umbral BIM · laboratorio motor de piezas · {_e(defin['fecha'])}</p>
<h1>{_e(defin['titulo'])}</h1>
<p class="desc">{_e(defin['descripcion'])}</p>
<p class="aviso">{_e(defin['como_elegir'])}</p>
<p class="desc">Hoja numerada: <a href="00_preview.jpg">00_preview.jpg</a>{' · detalle: <a href="01_detalle.jpg">01_detalle.jpg</a>' if defin.get('detalle') else ''} · registro: <a href="decisiones_{_e(defin['id'])}.csv">decisiones_{_e(defin['id'])}.csv</a></p>
<table class="indice"><tr><th>°</th><th>código</th><th>sección</th><th>formato</th><th>modo</th><th>imagen</th><th>estado</th></tr>
{''.join(f"<tr><td><a href='#p{_e(it['numero'].rstrip('°'))}'><b>{_e(it['numero'])}</b></a></td><td><code>{_e(it['codigo'])}</code></td>"
         f"<td>{_e(it['seccion'])}</td><td>{_e(it['formato'])} {it['ancho']}×{it['alto']}</td><td>{_e(it['modo'])}</td>"
         f"<td>{_e(it['imagen']['archivo'] if it.get('imagen') else 'isometría vectorial' if any(e for e in it['derivados']['zonas'] if e == 'ilustracion') else '—')}</td>"
         f"<td>{_e(it['estado'])}</td></tr>" for it in items)}</table>
{''.join(secciones)}
{f'<section><h2>Control · el motor regenera una pieza v2 elegida solo desde un pack</h2>{ctrl}</section>' if controles else ''}
<p class="meta">Motor {_e(items[0]['procedencia']['motor'])} · tokens colors_and_type.css sha256 {_e(items[0]['procedencia']['tokens_css_sha256'])} ·
lockups desde 02_Logotipo/Exportables/Lockup · fuentes Inter y JetBrains Mono (woff2 del Design System, OFL en fuentes/).</p>
</main></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--definicion', required=True)
    ap.add_argument('--publicar', action='store_true')
    a = ap.parse_args()
    construir(LAB / a.definicion, a.publicar)


if __name__ == '__main__':
    main()
