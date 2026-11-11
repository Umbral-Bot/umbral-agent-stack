"""Marca Umbral BIM para el motor: tokens, color, contraste y lockups.

Los valores se leen siempre de `colors_and_type.css` (fuente única de UB-3) y
de `02_Logotipo/Exportables/Lockup/`. Este módulo no declara ningún color.
"""
from __future__ import annotations

import re
from pathlib import Path


# -- tokens --------------------------------------------------------------------

def leer_tokens(css: Path) -> dict:
    """Devuelve {'claro': {...}, 'oscuro': {...}} con las variables --ub-* resueltas.

    El bloque `[data-ub-theme="light"], :root` vale para la raíz y el tema claro;
    `[data-ub-theme="dark"]` sobrescribe en oscuro. Las referencias var() se
    resuelven dentro de cada tema.
    """
    texto = re.sub(r'/\*.*?\*/', '', Path(css).read_text(encoding='utf-8'), flags=re.S)
    raiz, claro, oscuro = {}, {}, {}
    for selector, cuerpo in re.findall(r'([^{}]+)\{([^{}]*)\}', texto):
        variables = {k: v.strip() for k, v in re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', cuerpo)}
        if not variables:
            continue
        sel = selector.strip()
        es_oscuro = 'data-ub-theme="dark"' in sel
        if ':root' in sel:
            raiz.update(variables)
        if 'data-ub-theme="light"' in sel:
            claro.update(variables)
        if es_oscuro:
            oscuro.update(variables)
    temas = {'claro': {**raiz, **claro}, 'oscuro': {**raiz, **oscuro}}
    for tema in temas.values():
        for nombre in list(tema):
            tema[nombre] = _resolver_var(tema, tema[nombre])
    return temas


def _resolver_var(tema: dict, valor: str, profundidad: int = 0) -> str:
    if profundidad > 10:
        raise ValueError(f'var() circular: {valor}')

    def sustituir(m):
        return _resolver_var(tema, tema.get(m.group(1), m.group(0)), profundidad + 1)

    return re.sub(r'var\((--[\w-]+)\)', sustituir, valor)


# -- color ---------------------------------------------------------------------

def color_rgba(valor: str) -> tuple[int, int, int, float]:
    """'#RRGGBB' | 'rgba(r, g, b, a)' | 'rgb(r, g, b)' -> (r, g, b, a)."""
    v = valor.strip()
    if v.startswith('#') and len(v) == 7:
        return int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16), 1.0
    m = re.match(r'rgba?\(([^)]+)\)', v)
    if m:
        partes = [p.strip() for p in m.group(1).split(',')]
        r, g, b = (int(float(p)) for p in partes[:3])
        a = float(partes[3]) if len(partes) > 3 else 1.0
        return r, g, b, a
    raise ValueError(f'color no reconocido: {valor}')


def hex_de(rgb) -> str:
    return '#{:02X}{:02X}{:02X}'.format(*(int(round(c)) for c in rgb[:3]))


def componer(frente, fondo) -> tuple[float, float, float]:
    """Mezcla un color con alfa sobre un fondo opaco (en sRGB, como el navegador)."""
    r, g, b, a = frente if len(frente) == 4 else (*frente, 1.0)
    return tuple(a * c + (1 - a) * f for c, f in zip((r, g, b), fondo[:3]))


def luminancia(rgb) -> float:
    def canal(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(c1, c2) -> float:
    l1, l2 = sorted((luminancia(c1), luminancia(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


# -- lockups -------------------------------------------------------------------

def ruta_lockup(carpeta: Path, cfg: dict, composicion: str, variante: str) -> Path:
    nombre = cfg['patron'].format(composicion=cfg['composiciones'][composicion],
                                  variante=cfg['variantes'][variante])
    ruta = Path(carpeta) / nombre
    if not ruta.is_file():
        raise FileNotFoundError(f'lockup oficial no encontrado: {ruta}')
    return ruta


def leer_svg_oficial(ruta: Path) -> tuple[str, float, float]:
    """Contenido interno de un SVG oficial, tal cual, y su viewBox (ancho, alto)."""
    crudo = Path(ruta).read_text(encoding='utf-8')
    m = re.search(r'viewBox="([^"]+)"', crudo)
    if not m:
        raise ValueError(f'SVG sin viewBox: {ruta}')
    _, _, vw, vh = (float(v) for v in m.group(1).split())
    interior = re.sub(r'^.*?<svg[^>]*>', '', crudo, count=1, flags=re.S)
    interior = re.sub(r'</svg>\s*$', '', interior.strip())
    interior = re.sub(r'<title>.*?</title>', '', interior, flags=re.S)
    return interior.strip(), vw, vh


def fills_de(svg_interior: str) -> set[str]:
    return {f.upper() for f in re.findall(r'fill="(#[0-9A-Fa-f]{6})"', svg_interior)}
