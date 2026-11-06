#!/usr/bin/env python3
"""Genera imagenes.yaml (catálogo de la capa de imagen) leyendo cada PNG.

Midjourney deja en el PNG el prompt con sus parámetros y el Job ID (campo
`Description`). Este script los copia al catálogo para que cada imagen quede
registrada con herramienta, modelo, prompt, referencias de estilo, semilla y
proporción, sin transcribir nada a mano. Lo que el archivo no trae queda en
null y se declara.

Uso: python catalogar_imagenes.py   (lee la lista de ids de imagenes.fuente.yaml)
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml
from PIL import Image

LAB = Path(__file__).resolve().parent


def leer_metadatos(ruta: Path) -> dict:
    im = Image.open(ruta)
    desc = im.info.get('Description', '') or ''
    xmp = im.info.get('XML:com.adobe.xmp', '') or ''
    m = re.match(r'(?P<prompt>.*?)\s+(?P<params>--.*?)(?:\s+Job ID:\s*(?P<job>[\w-]+))?\s*$', desc)
    prompt = m.group('prompt').strip() if m else desc.strip() or None
    params = m.group('params').strip() if m else ''
    job = m.group('job') if m else None

    def opcion(nombre):
        mm = re.search(rf'--{nombre}\s+(\S+)', params)
        return mm.group(1) if mm else None

    origen = re.search(r'DigitalSourceType="([^"]+)"', xmp)
    return {
        'herramienta': 'Midjourney' if job else None,
        'modelo': f"v{opcion('v')}" if opcion('v') else None,
        'prompt': prompt,
        'parametros': params or None,
        'job_id': job,
        'referencias_estilo': {'sref': opcion('sref'), 'perfil': opcion('p') or opcion('profile')},
        'semilla': opcion('seed'),
        'proporcion_pedida': opcion('ar'),
        'tamano_px': list(im.size),
        'tipo_origen_iptc': origen.group(1).rsplit('/', 1)[-1] if origen else None,
        'autor': im.info.get('Author'),
        'sha256': hashlib.sha256(ruta.read_bytes()).hexdigest()[:16],
    }


def main():
    rutas = yaml.safe_load((LAB / 'rutas.yaml').read_text(encoding='utf-8'))
    fuente = yaml.safe_load((LAB / 'imagenes.fuente.yaml').read_text(encoding='utf-8'))
    carpeta = Path(rutas['marca']) / rutas['imagenes_mj']
    salida = {}
    for ident, editorial in fuente['imagenes'].items():
        ruta = carpeta / editorial['archivo']
        meta = leer_metadatos(ruta)
        salida[ident] = {**editorial, **meta}
    cabecera = ('# GENERADO por catalogar_imagenes.py desde los metadatos de cada PNG.\n'
                '# No editar a mano: los campos editoriales viven en imagenes.fuente.yaml.\n'
                '# null = el archivo de origen no trae ese dato (no se inventa).\n')
    texto = yaml.safe_dump({'carpeta': rutas['imagenes_mj'], 'imagenes': salida},
                           allow_unicode=True, sort_keys=False, width=100)
    (LAB / 'imagenes.yaml').write_text(cabecera + texto, encoding='utf-8')
    print(f'imagenes.yaml: {len(salida)} imágenes')


if __name__ == '__main__':
    main()
