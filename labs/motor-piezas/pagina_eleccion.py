"""Página ciega para elegir en el celular: alternativas y piezas numeradas, sin el voto de los jueces.

David elige por número («me gusta la 4; en el 1:1, la 30°»). Los jueces votan antes y su voto queda
sellado en jueces/votos/ hasta que David elige: así se puede medir si los jueces se van pareciendo a él
(ver jueces/README.md). La página no lleva recomendaciones ni descartes.

Uso:
  python pagina_eleccion.py --galeria G28 --salida <ruta.html>
"""
import argparse
import base64
import html
import io
import json
from pathlib import Path

import yaml
from PIL import Image

LAB = Path(__file__).resolve().parent
RUTAS = yaml.safe_load((LAB / 'rutas.yaml').read_text(encoding='utf-8'))
DIR_MAGNIFIC = Path(RUTAS['marca']) / RUTAS['imagenes_magnific']


def b64(im: Image.Image, calidad: int = 80) -> str:
    buf = io.BytesIO()
    im.convert('RGB').save(buf, 'JPEG', quality=calidad, optimize=True, progressive=True)
    return base64.b64encode(buf.getvalue()).decode()


def figura(ruta: Path, leyenda: str, ancho: int | None = None) -> str:
    im = Image.open(ruta)
    ancho = ancho or (1000 if im.width > im.height * 1.3 else 680)
    alto = round(im.height * ancho / im.width)
    return (f'<figure class="pieza"><img src="data:image/jpeg;base64,{b64(im.resize((ancho, alto), Image.LANCZOS))}" '
            f'width="{ancho}" height="{alto}" alt="{html.escape(leyenda)}"><figcaption>{leyenda}</figcaption></figure>')


def imagenes_de(contenido: str, catalogo: dict) -> list[tuple[Path, str]]:
    """La imagen principal y la apaisada de una alternativa, tal como salen de Magnific."""
    c = yaml.safe_load((LAB / contenido).read_text(encoding='utf-8'))
    salida, vistas = [], set()
    for clave, nombre in [('imagen', 'Imagen principal'), ('imagen_ancha', 'Imagen apaisada')]:
        ident = c.get(clave)
        if not ident or ident in vistas or ident not in catalogo:
            continue
        vistas.add(ident)
        info = catalogo[ident]
        nota = ' (se usa una parte)' if info.get('region') else ''
        ruta = DIR_MAGNIFIC / info['archivo']
        if ruta.exists():
            salida.append((ruta, f'{nombre} · {ident}{nota}'))
    return salida


def construir(gid: str) -> str:
    defin = yaml.safe_load((LAB / 'galerias' / f'{gid}.yaml').read_text(encoding='utf-8'))
    dir_g = LAB / 'salida' / gid
    piezas = json.loads((dir_g / 'galeria.json').read_text(encoding='utf-8'))['piezas']
    cat = yaml.safe_load((LAB / 'imagenes.magnific.yaml').read_text(encoding='utf-8'))
    catalogo = cat.get('imagenes', cat)
    bloques = []
    for n, sec in enumerate(defin['secciones'], 1):
        suf = sec.get('sufijo', '')
        propias = [p for p in piezas if p['codigo'].endswith('-' + suf)] if suf else []
        pasos = sec.get('pasos') or [p['formato'] for p in propias]
        imgs = ''.join(figura(r, t, 900) for r, t in imagenes_de(sec.get('contenido', defin['contenido']), catalogo))
        figs = ''.join(figura(dir_g / p['png'], f"{p['numero']} · {html.escape(paso)}")
                       for p, paso in zip(propias, pasos))
        rango = f"{propias[0]['numero']} a {propias[-1]['numero']}" if propias else ''
        desc = ' '.join(str(sec.get('descripcion', '')).split())
        bloques.append(
            f'<section class="alt" id="alt-{n}" aria-labelledby="t-{n}">'
            f'<h2 id="t-{n}"><span class="num">{n}</span><span>{html.escape(sec["titulo"])}</span></h2>'
            f'<p class="intro">{html.escape(desc)} <span class="rango">Piezas {rango}.</span></p>'
            + (f'<div class="grilla">{imgs}</div>' if imgs else '')
            + f'<div class="grilla">{figs}</div></section>')
    indice = ''.join(f'<li><a href="#alt-{n}"><b>{n}</b> {html.escape(s["titulo"])}</a></li>'
                     for n, s in enumerate(defin['secciones'], 1))

    def fuente(nombre):
        return base64.b64encode((dir_g / 'fuentes' / nombre).read_bytes()).decode()

    total = len(defin['secciones'])
    return f"""<title>{gid} · Elige por número</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Página ciega: alternativas numeradas 1..N y piezas numeradas como en decisiones_{gid}.csv. */
@font-face {{ font-family: "Inter"; font-weight: 400; font-display: swap;
  src: url(data:font/woff2;base64,{fuente('Inter-Regular.woff2')}) format("woff2"); }}
@font-face {{ font-family: "Inter"; font-weight: 600; font-display: swap;
  src: url(data:font/woff2;base64,{fuente('Inter-SemiBold.woff2')}) format("woff2"); }}
:root {{ --bg:#FAFAF9; --sup:#FFFFFF; --tx:#1F2328; --mu:#5B636E; --bo:#E2E3DF; --pt:#074E43; --ac:#0FA994;
  --texto: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#111418; --sup:#1A1F24; --tx:#ECEDEE; --mu:#9BA3AD; --bo:#262B31; --pt:#99F6E4; --ac:#2DD4BF; color-scheme: dark }} }}
:root[data-theme="dark"] {{ --bg:#111418; --sup:#1A1F24; --tx:#ECEDEE; --mu:#9BA3AD; --bo:#262B31; --pt:#99F6E4; --ac:#2DD4BF; color-scheme: dark }}
body {{ background: var(--bg); color: var(--tx); font-family: var(--texto); font-size: 16px; line-height: 1.5; margin: 0; }}
main {{ max-width: 1240px; margin: 0 auto; padding-block: 20px 48px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 40px; }}
header {{ display: grid; gap: 8px; }}
h1 {{ font-size: 1.35rem; font-weight: 600; margin: 0; text-wrap: balance; }}
header p, .intro {{ margin: 0; color: var(--mu); max-width: 70ch; }}
.como {{ background: var(--sup); border: 1px solid var(--bo); border-radius: 8px; padding: 12px 14px; display: grid; gap: 6px; }}
.como p {{ margin: 0; color: var(--tx); }}
nav ol {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }}
nav a {{ color: var(--tx); text-decoration: none; }}
nav b {{ display: inline-block; min-width: 1.6em; color: var(--pt); }}
.alt {{ display: grid; gap: 14px; min-width: 0; padding-top: 16px; border-top: 1px solid var(--bo); scroll-margin-top: 12px; }}
h2 {{ display: flex; gap: 12px; align-items: baseline; font-size: 1.1rem; font-weight: 600; margin: 0; }}
.num {{ flex: none; display: inline-grid; place-items: center; width: 2.2em; height: 2.2em; border-radius: 50%;
  background: var(--pt); color: var(--bg); font-size: 1.1rem; }}
.rango {{ color: var(--tx); }}
.grilla {{ display: grid; gap: 12px; grid-template-columns: repeat(2, minmax(0, 1fr)); }}
@media (max-width: 720px) {{ .grilla {{ grid-template-columns: minmax(0, 1fr); gap: 16px; }} }}
.pieza {{ margin: 0; display: grid; gap: 6px; min-width: 0; align-content: start; }}
.pieza img {{ display: block; width: 100%; height: auto; max-width: 100%; border: 1px solid var(--bo); border-radius: 4px; }}
figcaption {{ color: var(--mu); font-size: .9rem; }}
footer {{ color: var(--mu); font-size: .9rem; border-top: 1px solid var(--bo); padding-top: 14px; }}
</style>
<main>
  <header>
    <h1>{gid} · Elige por número</h1>
    <p>{html.escape(' '.join(str(defin.get('resumen', '')).split()))}</p>
    <div class="como">
      <p><b>Cómo responder:</b> el número de la alternativa que te gusta (1 a {total}) y, si quieres, piezas sueltas
      por su número. Por ejemplo: «la 4; en el 1:1, la 30°; ninguna de las 6 a 8». Una frase de por qué ayuda a los jueces.</p>
      <p>Los jueces ya votaron. Su voto queda guardado y te lo muestro después de que elijas.</p>
    </div>
    <nav aria-label="Alternativas"><ol>{indice}</ol></nav>
  </header>
  {''.join(bloques)}
  <footer>Laboratorio del motor de piezas: no publicar.</footer>
</main>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--galeria', required=True)
    ap.add_argument('--salida', required=True)
    a = ap.parse_args()
    destino = Path(a.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(construir(a.galeria), encoding='utf-8')
    print(destino, round(destino.stat().st_size / 1e6, 2), 'MB')


if __name__ == '__main__':
    main()
