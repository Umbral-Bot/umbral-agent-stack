"""Pedido de imagen a Magnific One con el kit «Umbral BIM», y registro de la imagen recibida.

Magnific hace solo la imagen; el texto, el logo y la verificación los pone el motor
(magnific-marca.md). Una imagen maestra por artículo sirve para todos los formatos: el
motor la recorta para la zona de imagen de cada uno.

  pedido     compone cada formato de los presets, mide su zona de imagen y escribe el
             pedido: proporción de la maestra, zona segura donde debe caber el sujeto y
             texto del pedido. No llama a Magnific ni gasta créditos.
  registrar  copia a 02_magnific una imagen ya generada y la anota con su procedencia en
             imagenes.magnific.yaml, para que un contenido la use con `imagen: <id>`.

Uso:
  python pedido_magnific.py pedido --preset presets/P02.yaml --preset presets/P03.yaml \\
      --contenido contenido/articulo-ejemplo.yaml --salida magnific/pedidos/articulo-ia-obra.json
  python pedido_magnific.py registrar --id mg-articulo-ia-obra --png ruta.png \\
      --meta creacion.json --pedido magnific/pedidos/articulo-ia-obra.json
"""
import argparse
import json
import shutil
from datetime import date
from pathlib import Path

import yaml
from PIL import Image

from motor import LAB, Compositor, Contexto, abrir_navegador, cargar_pack, cargar_yaml, sha16

KIT = {'id': 'hu2CvqLJlt', 'nombre': 'Umbral BIM'}
PLANTILLA = 'post-linkedin'          # «Imagen de artículo · 16:9, solo imagen» (el slug es el original)
MODELO = 'magnific-one'              # el único que aplica un kit de marca
PROPORCION = (16, 9)                 # la media geométrica de las zonas va de 0,8:1 a 3,6:1
CREDITOS_2K = 180                    # simulate_cost, 2026-11-10; se vuelve a simular antes de gastar


def ventana(comp, maestra: tuple[int, int]) -> tuple[float, ...]:
    """Parte visible de la maestra (fracciones x0, y0, x1, y1) con el mismo encuadre que Compositor.imagen_en."""
    z = comp.zonas['imagen']
    zx, zy, zw, zh = z['x'], z['y'], z['w'], z['h']
    if comp.v['imagen_registro'] == 'lienzo':
        mx, my, mw, mh = 0.0, 0.0, comp.W, comp.H
    else:
        mx, my, mw, mh = zx, zy, zw, zh
    iw, ih = maestra
    k = max(mw / iw, mh / ih)
    dw, dh = iw * k, ih * k
    fx, fy = comp.v['imagen_foco']
    x = min(mx, max(mx + mw - dw, mx + mw / 2 - fx * dw))
    y = min(my, max(my + mh - dh, my + mh / 2 - fy * dh))
    return (zx - x) / dw, (zy - y) / dh, (zx + zw - x) / dw, (zy + zh - y) / dh


def pedido(a):
    ctx = Contexto()
    contenido = cargar_yaml(a.contenido)
    formatos = []
    with abrir_navegador(ctx) as nav:
        nav.preparar_medicion(ctx.css_fuentes(nav.url('fuentes', '')))
        for ruta_preset in a.preset:
            preset = cargar_yaml(ruta_preset)
            for formato, ruta_pack in preset['formatos'].items():
                comp = Compositor(ctx, nav, cargar_pack(LAB / ruta_pack), contenido)
                comp.componer()
                z = comp.zonas.get('imagen')
                if not z:
                    formatos.append({'preset': preset['id'], 'formato': formato, 'pack': ruta_pack,
                                     'zona_px': None, 'nota': 'sin zona de imagen'})
                    continue
                v = ventana(comp, PROPORCION)
                formatos.append({'preset': preset['id'], 'formato': formato, 'pack': ruta_pack,
                                 'lienzo_px': [comp.W, comp.H],
                                 'zona_px': [round(z['w']), round(z['h'])],
                                 'proporcion_zona': round(z['w'] / z['h'], 2),
                                 'foco': list(comp.v['imagen_foco']),
                                 'registro': comp.v['imagen_registro'],
                                 'ventana_visible': [round(x, 3) for x in v]})
    vistas = [f['ventana_visible'] for f in formatos if f.get('zona_px')]
    if not vistas:
        raise SystemExit('ningún formato tiene zona de imagen')
    segura = [max(v[0] for v in vistas), max(v[1] for v in vistas),
              min(v[2] for v in vistas), min(v[3] for v in vistas)]
    ancho, alto = segura[2] - segura[0], segura[3] - segura[1]
    if ancho <= 0 or alto <= 0:
        raise SystemExit(f'las zonas no comparten un área visible con la maestra {PROPORCION}: {segura}')
    titulo = contenido['titulo']
    titulo = ' '.join(titulo) if isinstance(titulo, list) else titulo
    idea = contenido.get('imagen_idea') or f'«{titulo}». {contenido.get("cuerpo", "")}'.strip()
    texto = (f'Article image for: {idea} One clear subject that carries this idea. '
             f'Keep the whole subject inside the central {round(ancho * 100)} percent of the width and '
             f'{round(alto * 100)} percent of the height; the rest of the frame is calm off-white with faint '
             f'construction grid lines running to the edges, because the image is cropped to every format. '
             f'No text, letters, numbers, labels or logos.')
    salida = {
        'contenido': str(Path(a.contenido).as_posix()),
        'fecha': date.today().isoformat(),
        'estado': 'pedido sin enviar: generar gasta créditos y necesita el OK de David',
        'magnific': {'herramienta': 'images_generate', 'modelo': MODELO, 'kit': KIT, 'plantilla': PLANTILLA,
                     'proporcion': f'{PROPORCION[0]}:{PROPORCION[1]}', 'resolucion': '2k',
                     'creditos_estimados': CREDITOS_2K,
                     'aviso': 'la plantilla queda fijada en 4:5 por su canal: el pedido pide 16:9 explícito'},
        'zona_segura': {'fracciones': [round(x, 3) for x in segura],
                        'ancho_pct': round(ancho * 100), 'alto_pct': round(alto * 100)},
        'texto': texto,
        'formatos': formatos,
    }
    destino = LAB / a.salida
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{destino}: {len(vistas)} formatos con imagen; zona segura {salida["zona_segura"]["ancho_pct"]} % × '
          f'{salida["zona_segura"]["alto_pct"]} % de la maestra {PROPORCION[0]}:{PROPORCION[1]}')
    for f in formatos:
        print(f"  {f['preset']} {f['formato']:10s} zona {f.get('zona_px')} ({f.get('proporcion_zona')}:1)"
              f" visible {f.get('ventana_visible')}")


def registrar(a):
    """La imagen entra con su procedencia; sin creación ni créditos anotados no entra."""
    ctx = Contexto()
    meta = json.loads(Path(a.meta).read_text(encoding='utf-8'))
    md = meta.get('metadata') or {}
    for clave in ('identifier',):
        if not meta.get(clave):
            raise SystemExit(f'--meta no trae {clave}: guarda la salida de creations_get')
    origen = Path(a.png)
    with Image.open(origen) as im:
        ancho, alto = im.size
    ctx.dir_magnific.mkdir(parents=True, exist_ok=True)
    archivo = f'{a.id}{origen.suffix.lower()}'
    destino = ctx.dir_magnific / archivo
    if destino.exists():
        raise SystemExit(f'ya existe {destino}: usa otro --id')
    shutil.copy2(origen, destino)
    ruta_cat = LAB / 'imagenes.magnific.yaml'
    cat = cargar_yaml(ruta_cat) if ruta_cat.exists() else {}
    imagenes = cat.get('imagenes') or {}
    if a.id in imagenes or a.id in cargar_yaml(LAB / 'imagenes.yaml')['imagenes']:
        raise SystemExit(f'el id {a.id} ya está en un catálogo')
    imagenes[a.id] = {
        'archivo': archivo,
        'herramienta': 'Magnific',
        'modelo': md.get('mode') or md.get('slug'),
        'creacion': meta['identifier'],
        'enlace': meta.get('webUrl', '').split('?')[0] or None,
        'kit': md.get('brandKitId') or a.kit or None,
        'plantilla': md.get('templateSlug') or a.plantilla or None,
        'semilla': md.get('seed'),
        'creditos': md.get('credits'),
        'prompt': md.get('prompt'),                 # el que compuso Magnific con el kit
        'prompt_enviado': md.get('inputPrompt'),
        'proporcion_pedida': a.proporcion,
        'tamano_px': [ancho, alto],
        'reproducible': md.get('seed') is not None,
        'pedido': a.pedido,
        'fecha': (meta.get('createdAt') or date.today().isoformat())[:10],
        'sha256': sha16(destino),
    }
    if a.nota:
        imagenes[a.id]['nota'] = a.nota
    if a.foco:
        imagenes[a.id]['foco'] = [float(x) for x in a.foco.split(',')]
    cabecera = ('# Imágenes de Magnific One con el kit «Umbral BIM». Las escribe pedido_magnific.py registrar.\n'
                '# El archivo vive en 07_Motor de piezas/02_magnific; la procedencia, aquí.\n')
    ruta_cat.write_text(cabecera + yaml.safe_dump({'imagenes': imagenes}, allow_unicode=True, sort_keys=False,
                                                  width=100), encoding='utf-8')
    print(f'{a.id}: {destino} ({ancho}×{alto}) anotada en {ruta_cat.name}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='orden', required=True)
    p = sub.add_parser('pedido', help='mide las zonas de imagen y escribe el pedido (sin créditos)')
    p.add_argument('--preset', action='append', required=True)
    p.add_argument('--contenido', required=True)
    p.add_argument('--salida', required=True)
    r = sub.add_parser('registrar', help='copia una imagen generada y la anota con su procedencia')
    r.add_argument('--id', required=True)
    r.add_argument('--png', required=True)
    r.add_argument('--meta', required=True, help='salida de creations_get guardada como JSON')
    r.add_argument('--pedido', help='pedido del que salió la imagen')
    r.add_argument('--kit', default=KIT['id'])
    r.add_argument('--plantilla', default=PLANTILLA)
    r.add_argument('--proporcion', default=f'{PROPORCION[0]}:{PROPORCION[1]}')
    r.add_argument('--nota')
    r.add_argument('--foco', help='x,y del sujeto en fracciones (p. ej. el centro del turquesa)')
    a = ap.parse_args()
    pedido(a) if a.orden == 'pedido' else registrar(a)


if __name__ == '__main__':
    main()
