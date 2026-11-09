#!/usr/bin/env python3
"""Motor paramétrico de piezas gráficas Umbral BIM · laboratorio (v0.2).

Entra un pack (valores con nombre) y un contenido; sale la pieza en SVG y PNG.

Ningún valor de diseño vive en este archivo. Formatos, proporciones, tamaños,
espacios y roles de color salen de `parametros.borrador.yaml` (defectos) y del
pack; los colores, de `colors_and_type.css`; los logotipos, de
`02_Logotipo/Exportables/Lockup/`; los textos, del contenido; las imágenes, de
`imagenes.yaml`. El código solo sabe *cómo* componer.

Base: la lógica de `generate.py` de la v2 (copia portable del Director en
07_Motor de piezas/00_insumos/01_codigo/), con sus valores sacados a parámetros.
El raster lo hace Chrome (navegador.py) en lugar de CairoSVG.

Uso:
  python motor.py pieza --pack packs/A1.yaml [--contenido contenido/x.yaml] [--salida salida/prueba]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import numpy as np
import yaml
from PIL import Image

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))   # solo los módulos del laboratorio (funciona también con python -I)

import marca  # noqa: E402
from navegador import Navegador  # noqa: E402

VERSION_MOTOR = '0.3'


def cargar_yaml(ruta) -> dict:
    return yaml.safe_load(Path(ruta).read_text(encoding='utf-8'))


def cargar_pack(ruta) -> dict:
    """Lee un pack. Con `hereda: packs/X.yaml` parte de otro pack y cambia solo sus propios valores:
    así cada preset de un paso muestra exactamente qué cambió respecto de la base."""
    pack = cargar_yaml(ruta)
    if not pack.get('hereda'):
        return pack
    padre = cargar_pack(LAB / pack['hereda'])
    hijo = dict(pack)
    pack = {**padre, **hijo,
            'valores': {**(padre.get('valores') or {}), **(hijo.get('valores') or {})},
            'roles_texto': {**(padre.get('roles_texto') or {}), **(hijo.get('roles_texto') or {})} or None}
    for clave in ('control', 'exploracion', 'decision_david', 'corrige', 'recorrido', 'estado',
                  'tipo_contenido'):   # propios de cada pack
        if clave not in hijo:
            pack.pop(clave, None)
    return pack


def sha16(ruta: Path) -> str:
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()[:16]


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self):
        return self.x + self.w

    @property
    def y2(self):
        return self.y + self.h

    def interseca(self, otro: 'Rect', holgura: float = 0.0) -> bool:
        return not (self.x2 <= otro.x + holgura or otro.x2 <= self.x + holgura
                    or self.y2 <= otro.y + holgura or otro.y2 <= self.y + holgura)

    def a_dict(self):
        return {'x': round(self.x, 1), 'y': round(self.y, 1), 'w': round(self.w, 1), 'h': round(self.h, 1)}


# -----------------------------------------------------------------------------
# contexto y parámetros
# -----------------------------------------------------------------------------

class Contexto:
    """Todo lo que el motor lee de fuera: rutas, esquema, tokens, catálogo."""

    def __init__(self):
        self.rutas = cargar_yaml(LAB / 'rutas.yaml')
        self.marca = Path(self.rutas['marca'])
        self.esquema = cargar_yaml(LAB / 'parametros.borrador.yaml')
        self.reglas = self.esquema['reglas_fijas_manual_ub3']
        self.ruta_tokens = self.marca / self.rutas['tokens_css']
        self.tokens = marca.leer_tokens(self.ruta_tokens)
        self.dir_fuentes = self.marca / self.rutas['fuentes']
        self.dir_lockups = self.marca / self.rutas['lockups']
        self.dir_mj = self.marca / self.rutas['imagenes_mj']
        self.catalogo = cargar_yaml(LAB / 'imagenes.yaml')['imagenes']
        self.ilustraciones = self.rutas['ilustraciones']

    def css_fuentes(self, prefijo: str) -> str:
        return ''.join(
            f"@font-face{{font-family:'{f['familia']}';font-style:normal;font-weight:{f['peso']};"
            f"src:url('{prefijo}{f['archivo']}') format('woff2');}}"
            for f in self.rutas['archivos_fuentes'])

    def copiar_fuentes(self, destino: Path):
        destino.mkdir(parents=True, exist_ok=True)
        for f in self.rutas['archivos_fuentes']:
            shutil.copy2(self.dir_fuentes / f['archivo'], destino / f['archivo'])
        for lic in self.rutas['licencias_fuentes']:   # la OFL viaja con las fuentes
            shutil.copy2(self.dir_fuentes / lic, destino / lic)


def resolver_valores(esquema: dict, pack: dict) -> dict:
    """Defectos del esquema + valores del pack, validados contra tipo y rango."""
    params = esquema['parametros']
    valores = {k: p.get('defecto') for k, p in params.items()}
    propios = pack.get('valores') or {}
    desconocidos = sorted(set(propios) - set(params))
    if desconocidos:
        raise ValueError(f"parámetros desconocidos en el pack {pack.get('id')}: {desconocidos}")
    valores.update(propios)
    errores = []
    for k, p in params.items():
        v = valores[k]
        if v is None:
            continue
        t = p['tipo']
        if t == 'opcion' and v not in p['opciones']:
            errores.append(f'{k}={v!r} no está en {p["opciones"]}')
        elif t == 'entero' and (isinstance(v, bool) or not isinstance(v, int)):
            errores.append(f'{k}={v!r} debe ser entero')
        elif t == 'decimal' and (isinstance(v, bool) or not isinstance(v, (int, float))):
            errores.append(f'{k}={v!r} debe ser número')
        elif t == 'booleano' and not isinstance(v, bool):
            errores.append(f'{k}={v!r} debe ser true/false')
        elif t == 'par' and not (isinstance(v, list) and len(v) == 2):
            errores.append(f'{k}={v!r} debe ser [a, b]')
        if t in ('entero', 'decimal') and p.get('rango') and isinstance(v, (int, float)):
            lo, hi = p['rango']
            if not lo <= v <= hi:
                errores.append(f'{k}={v} fuera del rango {p["rango"]}')
    if errores:
        raise ValueError(f"pack {pack.get('id')} inválido:\n  " + '\n  '.join(errores))
    return valores


# -----------------------------------------------------------------------------
# utilidades numéricas de contraste sobre píxeles
# -----------------------------------------------------------------------------

def _lineal(c):
    c = np.asarray(c, dtype=float) / 255.0
    return np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def luminancias(px: np.ndarray) -> np.ndarray:
    lin = _lineal(px)
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


def contrastes(rgb_texto, px: np.ndarray) -> np.ndarray:
    lt = marca.luminancia(rgb_texto)
    lb = luminancias(px)
    return (np.maximum(lt, lb) + 0.05) / (np.minimum(lt, lb) + 0.05)


# -----------------------------------------------------------------------------
# el compositor
# -----------------------------------------------------------------------------

class Compositor:
    PERCENTIL_CONTRASTE = 10   # el 10 % más desfavorable del fondo bajo cada texto

    def __init__(self, ctx: Contexto, nav: Navegador, pack: dict, contenido: dict):
        self.ctx, self.nav = ctx, nav
        self.pack = pack
        self.c = contenido
        self.v = resolver_valores(ctx.esquema, pack)
        self.roles_texto = {k: dict(r) for k, r in ctx.esquema['roles_texto'].items()}
        for rol, cambios in (pack.get('roles_texto') or {}).items():
            self.roles_texto[rol].update(cambios)
        fmt = ctx.esquema['formatos'][self.v['formato']]
        # la vista supuesta (px CSS) puede venir del pack; si no, la del formato
        self.W, self.H, self.vista = fmt['ancho'], fmt['alto'], self.v['vista_css'] or fmt['vista_css']
        self.s = min(self.W, self.H)
        self.paso4 = ctx.reglas['espaciado_multiplo_px']
        self.modo = self.v['modo']
        self.tema = ctx.tokens[self.modo]
        self.colores = self._resolver_colores()
        self.el: list[dict] = []          # elementos en orden de pintado
        self.velos: list[dict] = []
        self.imagen: dict | None = None
        self.logo: dict | None = None
        self.notas: list[str] = []
        self.notas_fijas: list[str] = []  # notas que no se descartan al medir la pila de prueba
        if contenido.get('imagen'):
            # la imagen puede venir con el contenido: cada artículo trae la suya
            if contenido['imagen'] not in ctx.catalogo:
                raise ValueError(f"la imagen {contenido['imagen']!r} del contenido no está en imagenes.yaml")
            if contenido['imagen'] != self.v['imagen_fuente']:
                self.notas.append(f"imagen del contenido: {contenido['imagen']} (el pack traía {self.v['imagen_fuente']})")
            self.v['imagen_fuente'] = contenido['imagen']
        self.zonas: dict[str, dict] = {}
        self.fondo = None                 # raster 1x del fondo (color + imagen) para medir contraste

    # ---------------------------------------------------------------- color
    def _resolver_colores(self) -> dict:
        roles = self.ctx.esquema['roles_color'][self.modo]
        col = {rol: self.tema[token] for rol, token in roles.items()}
        tokens = dict(roles)
        if self.v['fondo_portada']:
            token = self.ctx.esquema['roles_color']['fondo_portada']
            col['fondo'] = col['velo'] = self.tema[token]
            tokens['fondo'] = tokens['velo'] = token
        self.tokens_usados = tokens
        return col

    def rgba(self, rol: str):
        return marca.color_rgba(self.colores[rol])

    def rgb_opaco(self, rol: str):
        """Color del rol mezclado sobre el fondo (los tokens rgba del tema oscuro)."""
        return marca.componer(self.rgba(rol), self.rgba('fondo'))

    def pintura(self, rol: str) -> str:
        r, g, b, a = self.rgba(rol)
        relleno = marca.hex_de((r, g, b))
        return f'fill="{relleno}"' + (f' fill-opacity="{a:g}"' if a < 1 else '')

    # ---------------------------------------------------------------- grilla
    def r4(self, valor: float) -> float:
        return max(self.paso4, self.paso4 * round(valor / self.paso4))

    def preparar_grilla(self):
        v = self.v
        self.margen = self.r4(v['margen_proporcional'] * self.s)
        mi = v['margen_inferior_proporcional']
        self.margen_inf = self.r4(mi * self.s) if mi else self.margen
        self.medianil = self.r4(v['medianil_proporcional'] * self.s)
        self.modulo = self.r4(v['modulo_proporcional'] * self.s)
        self.caja = Rect(self.margen, self.margen, self.W - 2 * self.margen,
                         self.H - self.margen - self.margen_inf)
        self.N, self.M = v['columnas'], v['filas']
        self.col_w = (self.caja.w - (self.N - 1) * self.medianil) / self.N
        self.fil_h = (self.caja.h - (self.M - 1) * self.medianil) / self.M

    def x_col(self, i: int) -> float:
        return self.caja.x + i * (self.col_w + self.medianil)

    def y_fil(self, j: int) -> float:
        return self.caja.y + j * (self.fil_h + self.medianil)

    def celdas(self, c0: int, c1: int, f0: int, f1: int) -> Rect:
        """Columnas c0..c1-1 y filas f0..f1-1 de la grilla."""
        x, y = self.x_col(c0), self.y_fil(f0)
        return Rect(x, y, self.x_col(c1 - 1) + self.col_w - x, self.y_fil(f1 - 1) + self.fil_h - y)

    def mod(self, n: int) -> float:
        return n * self.modulo

    # ---------------------------------------------------------------- texto
    def estilo(self, rol: str) -> dict:
        r = self.roles_texto[rol]
        tracking = self.v[r['tracking']] if r.get('tracking') else 0.0
        return {'familia': r['familia'], 'peso': r['peso'], 'mayus': r['mayusculas'],
                'tracking_em': tracking, 'color': r['color']}

    def rasgos(self, familia: str) -> str:
        return self.ctx.reglas['rasgos_opentype'] if familia == 'Inter' else 'normal'

    def preparar_texto(self, rol: str, texto: str) -> str:
        return texto.upper() if self.estilo(rol)['mayus'] else texto

    def medir(self, rol: str, texto: str, tamano: float) -> dict:
        e = self.estilo(rol)
        return self.nav.medir([{'texto': texto, 'familia': e['familia'], 'peso': e['peso'],
                                'tamano': tamano, 'tracking_em': e['tracking_em'],
                                'rasgos': self.rasgos(e['familia'])}])[0]

    def preparar_tamanos(self):
        """Tamaños por rol desde el texto mínimo en px CSS del dispositivo del formato."""
        k = self.W / self.vista
        base = round(self.v['texto_minimo_css'] * k, 1)
        self.t = {'etiqueta': base}
        for rol in ('kicker', 'subtitulo', 'cta', 'valor', 'numero', 'cuerpo', 'chip'):
            self.t[rol] = round(base * self.v[f'escala_{rol}'], 1)
        self.px_por_css = k
        self.t_base = dict(self.t)
        self.cap_titulo = self.medir('titulo', 'H', 1000)['cap'] / 1000

    def agregar_texto(self, id_: str, rol: str, texto: str, x: float, base: float, tamano: float,
                      anclaje: str = 'start', color: str | None = None) -> dict:
        e = self.estilo(rol)
        t = self.preparar_texto(rol, texto)
        m = self.medir(rol, t, tamano)
        ancho = m['avance']
        x0 = x if anclaje == 'start' else (x - ancho if anclaje == 'end' else x - ancho / 2)
        el = {'tipo': 'texto', 'id': id_, 'rol': rol, 'texto': t, 'x': x, 'y': base, 'tamano': tamano,
              'familia': e['familia'], 'peso': e['peso'], 'tracking_em': e['tracking_em'],
              'anclaje': anclaje, 'color': color or e['color'],
              'caja': Rect(x0, base - m['asc'], ancho, m['asc'] + m['desc']), 'cap': m['cap']}
        self.el.append(el)
        return el

    def partir(self, rol: str, texto: str, tamano: float, ancho: float) -> list[str]:
        """Parte un texto en líneas que caben en `ancho`; nunca deja un «·» al borde de una línea."""
        t = self.preparar_texto(rol, texto)
        if self.medir(rol, t, tamano)['avance'] <= ancho:
            return [t]

        def llenar(unidades, sep):
            lineas, actual = [], ''
            for u in unidades:
                prueba = f'{actual}{sep}{u}' if actual else u
                if not actual or self.medir(rol, prueba, tamano)['avance'] <= ancho:
                    actual = prueba
                else:
                    lineas.append(actual)
                    actual = u
            lineas.append(actual)
            return lineas

        # se corta primero en los «·»; si un tramo no cabe solo, por palabras
        tramos = [x.strip() for x in t.split('·') if x.strip()]
        if len(tramos) > 1 and all(self.medir(rol, x, tamano)['avance'] <= ancho for x in tramos):
            lineas = llenar(tramos, ' · ')
        else:
            lineas = llenar(t.split(' '), ' ')
        lineas = [l.strip(' ·').strip() for l in lineas]
        lineas = [l for l in lineas if l]
        if len(lineas) > 1:
            self.notas.append(f'{rol} partido en {len(lineas)} líneas para caber en {ancho:.0f} px')
        return lineas

    def tamano_titulo(self, ancho_zona: float, modo: str = 'tope') -> float:
        """Altura de mayúscula objetivo, reducida si la línea más larga no cabe en la zona."""
        lineas = [self.preparar_texto('titulo', l) for l in self.c['titulo']]
        tam = self.v['titulo_altura_relativa'] * self.H / self.cap_titulo
        mayor = max(self.medir('titulo', l, tam)['avance'] for l in lineas)
        limite = ancho_zona * self.v['titulo_ancho_max']
        if mayor > limite:
            nuevo = round(tam * limite / mayor, 1)
            self.notas.append(f'título reducido de {tam:.0f} a {nuevo:.0f} px para caber en {ancho_zona:.0f} px')
            tam = nuevo
        return round(tam, 1)

    # ---------------------------------------------------------------- filas
    def medidas_filas(self, filas: list) -> dict:
        v, t = self.v, self.t
        cap_et = self.medir('etiqueta', 'H', t['etiqueta'])['cap']
        cap_val = self.medir('valor', 'H', t['valor'])['cap']
        cap_num = self.medir('numero', '0', t['numero'])['cap']
        alto = (self.mod(v['fila_relleno_superior']) + cap_et + self.mod(v['fila_separacion_interna'])
                + cap_val + self.mod(v['fila_relleno_inferior']))
        ancho_num = max(self.medir('numero', f['numero'], t['numero'])['avance'] for f in filas)
        dx_txt = self.mod(v['fila_x_numero']) + ancho_num + self.mod(v['fila_espacio_numero_texto'])
        ancho_txt = max(max(self.medir('valor', f['valor'], t['valor'])['avance'],
                            self.medir('etiqueta', self.preparar_texto('etiqueta', f['etiqueta']),
                                       t['etiqueta'])['avance']) for f in filas)
        return {'alto': alto, 'cap_et': cap_et, 'cap_val': cap_val, 'cap_num': cap_num,
                'dx_txt': dx_txt, 'ancho_min': dx_txt + ancho_txt, 'total': alto * len(filas)}

    def ajustar_datos_al_ancho(self, filas: list, ancho: float):
        """Si las filas no caben en el ancho, achica valor y número juntos, nunca por debajo de la etiqueta."""
        if self.medidas_filas(filas)['ancho_min'] <= ancho + 0.5:
            return
        antes, razon = self.t['valor'], self.t['numero'] / self.t['valor']
        lo, hi = self.t['etiqueta'], self.t['valor']
        for _ in range(14):
            mid = (lo + hi) / 2
            self.t['valor'], self.t['numero'] = mid, mid * razon
            lo, hi = (mid, hi) if self.medidas_filas(filas)['ancho_min'] <= ancho else (lo, mid)
        lo = math.floor(lo * 10) / 10
        self.t['valor'], self.t['numero'] = lo, math.floor(lo * razon * 10) / 10
        self.notas_fijas.append(f'datos reducidos de {antes:.0f} a {lo:.0f} px para caber en {ancho:.0f} px')

    def bloque_filas(self, filas: list, x: float, y: float, ancho: float) -> float:
        """Filas numeradas con filetes y cruces. Devuelve la y del último filete."""
        v, t = self.v, self.t
        m = self.medidas_filas(filas)
        if m['ancho_min'] > ancho:
            self.notas.append(f'filas: el texto necesita {m["ancho_min"]:.0f} px y la zona tiene {ancho:.0f}')
        cruz = v['cruz_tamano_rel'] * self.s
        x_num = x + self.mod(v['fila_x_numero'])
        x_txt = x + m['dx_txt']
        for i, f in enumerate(filas + [None]):
            yy = y + i * m['alto']
            self.el.append({'tipo': 'linea', 'id': f'fila-filete-{i}', 'x1': x, 'y1': yy, 'x2': x + ancho,
                            'y2': yy, 'color': 'filete'})
            if v['filas_cruces']:
                for cx in (x, x + ancho):
                    self.el.append({'tipo': 'cruz', 'cx': cx, 'cy': yy, 'tam': cruz, 'color': 'acento'})
            if f is None:
                break
            n = f['numero']
            base_et = yy + self.mod(v['fila_relleno_superior']) + m['cap_et']
            base_val = base_et + self.mod(v['fila_separacion_interna']) + m['cap_val']
            centro = (base_et - m['cap_et'] + base_val) / 2
            self.agregar_texto(f'fila-{n}-numero', 'numero', n, x_num, centro + m['cap_num'] / 2, t['numero'])
            self.agregar_texto(f'fila-{n}-etiqueta', 'etiqueta', f['etiqueta'], x_txt, base_et, t['etiqueta'])
            self.agregar_texto(f'fila-{n}-valor', 'valor', f['valor'], x_txt, base_val, t['valor'])
        self.zonas['filas'] = Rect(x, y, ancho, m['total']).a_dict()
        return y + m['total']

    def filas_activas(self) -> list:
        dens = self.ctx.esquema['densidades'][self.v['densidad_texto']]
        return [f for f in (self.c.get('filas') or []) if f.get('densidad', 'minima') in dens['filas']]

    # ---------------------------------------------------------------- pila de texto
    def pila(self, zona: Rect, tam_titulo: float, ubicacion_filas: str, ancho_filas: float | None = None,
             anclar_abajo: bool = False, filas_a_grilla: bool = False, cta_en_pila: bool = False,
             zona_filas: Rect | None = None, ancho_cabecera: float | None = None,
             solo_medir: bool = False) -> dict | float:
        """Kicker, título, subtítulo, filas y cuerpo, de arriba abajo, en `zona`.

        Con ubicacion_filas='columna_derecha' las filas van en `zona_filas`, con su
        primer filete alineado a la línea de mayúscula del título. Con 'aparte', la pila
        no pone filas (las ubica quien la llama). Con solo_medir devuelve el alto que
        ocuparía, sin agregar nada a la pieza.
        """
        notas_antes = list(self.notas)
        v, t = self.v, self.t
        tope = v['jerarquia_tope_secundario']
        if tope:
            # el kicker y el subtítulo no pasan de `tope` veces el título (nunca bajo el texto mínimo)
            for rol in ('kicker', 'subtitulo'):
                t[rol] = max(self.t_base['etiqueta'], min(self.t_base[rol], round(tope * tam_titulo, 1)))
        dens = self.ctx.esquema['densidades'][v['densidad_texto']]
        centrada = v['alineacion'] == 'centrada'
        ancla = 'middle' if centrada else 'start'
        xt = zona.x + zona.w / 2 if centrada else zona.x
        filas = self.filas_activas()
        con_filas_en_pila = bool(filas) and ubicacion_filas == 'bajo_titulo'
        ancho_filas = ancho_filas or zona.w
        if filas and v['datos_ajuste_ancho']:
            self.ajustar_datos_al_ancho(filas, zona_filas.w if ubicacion_filas == 'columna_derecha'
                                        and zona_filas is not None else ancho_filas)

        # 1. plan relativo (y = 0 es la línea de mayúscula del primer bloque)
        plan, y = [], 0.0
        previo = None   # línea base (o filete) del bloque anterior

        def separar(n_modulos):
            return 0.0 if previo is None else previo + self.mod(n_modulos)

        def bloque(id_, rol, texto, n_modulos):
            """Agrega un texto que parte línea si no cabe en la zona. Devuelve la última línea base."""
            tam = t[rol]
            cap = self.medir(rol, 'H', tam)['cap']
            ancho = (ancho_cabecera or zona.w) if rol in ('kicker', 'subtitulo') else zona.w
            lineas_b = self.partir(rol, texto, tam, ancho)
            primera = separar(n_modulos) + cap
            for i, linea in enumerate(lineas_b):
                sufijo = '' if len(lineas_b) == 1 else f'-{i + 1}'
                plan.append(('texto', f'{id_}{sufijo}', rol, linea, primera + i * tam * v['texto_interlineado'],
                             tam, None))
            return primera + (len(lineas_b) - 1) * tam * v['texto_interlineado']

        if dens['kicker'] and self.c.get('kicker'):
            previo = bloque('kicker', 'kicker', self.c['kicker'], 0)
        cap_t = tam_titulo * self.cap_titulo
        tope = separar(v['espacio_kicker_titulo'])
        tope_titulo_rel = tope
        acento = v['titulo_linea_acento'] == 'ultima'
        lineas = self.c['titulo']
        for i, linea in enumerate(lineas):
            base = tope + cap_t + i * tam_titulo * v['titulo_interlineado']
            color = 'acento_texto' if acento and i == len(lineas) - 1 else None
            plan.append(('texto', f'titulo-{i + 1}', 'titulo', linea, base, tam_titulo, color))
        previo = base
        fondo_titulo = base + self.medir('titulo', self.preparar_texto('titulo', lineas[-1]), tam_titulo)['desc']
        if dens['subtitulo'] and self.c.get('subtitulo'):
            previo = bloque('subtitulo', 'subtitulo', self.c['subtitulo'], v['espacio_titulo_subtitulo'])
        fondo_cabecera = previo
        if con_filas_en_pila:
            tope = separar(v['espacio_subtitulo_filas'])
            plan.append(('filas', tope))
            previo = tope + self.medidas_filas(filas)['total']
        if dens['cuerpo'] and self.c.get('cuerpo'):
            previo = bloque('cuerpo', 'cuerpo', self.c['cuerpo'], v['espacio_filas_cuerpo'])
        # si el llamado no cabe en el pie y las filas van al pie, el llamado va bajo las filas
        hay_cta = cta_en_pila and dens['cta'] and self.c.get('cta') and v['cta_visible']
        cta_bajo_filas = bool(hay_cta and filas and ubicacion_filas == 'al_pie')
        boton = v['cta_estilo'] == 'boton'
        alto_cta = (self.mod(v['espacio_filas_cuerpo'])
                    + (self.alto_boton_cta() if boton else self.medir('cta', 'H', t['cta'])['cap'])
                    if cta_bajo_filas else 0.0)
        if hay_cta and not cta_bajo_filas:
            previo = bloque('cta', 'cta', self.c['cta'], v['espacio_filas_cuerpo'])
        alto = previo or 0.0
        if not solo_medir and self.notas_fijas:
            self.notas += self.notas_fijas
            self.notas_fijas = []
        if solo_medir:
            self.notas = notas_antes + self.notas_fijas
            self.notas_fijas = []
            if filas and ubicacion_filas == 'columna_derecha':
                alto = max(alto, tope_titulo_rel + self.medidas_filas(filas)['total'])
            elif filas and ubicacion_filas == 'al_pie':
                alto += self.mod(v['espacio_subtitulo_filas']) + self.medidas_filas(filas)['total'] + alto_cta
            return alto

        # 2. posición absoluta
        y0 = zona.y + self.mod(v['pila_desplazamiento'])
        if anclar_abajo:
            y0 = zona.y2 - alto
        if filas_a_grilla and con_filas_en_pila:
            # la grilla manda: el bloque de filas arranca en la siguiente línea de fila
            tope_rel = next(p[1] for p in plan if p[0] == 'filas')
            libre = [j for j in range(self.M) if self.y_fil(j) >= y0 + tope_rel - 0.5]
            if libre:
                corrimiento = self.y_fil(libre[0]) - (y0 + tope_rel)
                plan = [(p[0], p[1] + corrimiento) if p[0] == 'filas' else
                        ((*p[:4], p[4] + corrimiento, *p[5:]) if p[1].split('-')[0] in ('cuerpo', 'cta') else p)
                        for p in plan]
                alto += corrimiento
        for p in plan:
            if p[0] == 'filas':
                self.bloque_filas(filas, zona.x, y0 + p[1], ancho_filas)
            else:
                _, id_, rol, texto, base, tam, color = p
                self.agregar_texto(id_, rol, texto, xt, y0 + base, tam, ancla, color)
        fondo = y0 + alto
        tope_titulo = next(y0 + p[4] - cap_t for p in plan if p[0] == 'texto' and p[1] == 'titulo-1')
        info = {'tope': y0, 'fondo': fondo, 'fondo_pila': fondo, 'fondo_titulo': y0 + fondo_titulo,
                'fondo_cabecera': y0 + fondo_cabecera, 'filas': None, 'tope_titulo': tope_titulo}

        # 3. filas fuera de la pila
        if filas and ubicacion_filas == 'columna_derecha' and zona_filas is not None:
            m = self.medidas_filas(filas)
            info['fondo_filas'] = self.bloque_filas(filas, zona_filas.x, tope_titulo, zona_filas.w)
            info['filas'] = Rect(zona_filas.x, tope_titulo, zona_filas.w, m['total'])
            if info['fondo_filas'] > zona_filas.y2 + 0.5:
                self.notas.append('filas en columna derecha: no caben en la altura disponible')
        if filas and ubicacion_filas == 'al_pie':
            m = self.medidas_filas(filas)
            tope = zona.y2 - m['total'] - alto_cta
            if tope < fondo + self.mod(v['espacio_subtitulo_filas']):
                self.notas.append('filas al pie no caben bajo el título: van bajo el título')
                tope = fondo + self.mod(v['espacio_subtitulo_filas'])
            if filas_a_grilla:
                candidatas = [self.y_fil(j) + self.fil_h for j in range(self.M)
                              if self.y_fil(j) + self.fil_h <= zona.y2 - alto_cta + 0.5]
                if candidatas:
                    tope = max(tope, candidatas[-1] - m['total'])
            info['fondo'] = self.bloque_filas(filas, zona.x, tope, ancho_filas)
            info['filas'] = Rect(zona.x, tope, ancho_filas, m['total'])
            if cta_bajo_filas:
                if boton:
                    h = self.alto_boton_cta()
                    caja = self.boton_cta(xt, info['fondo'] + alto_cta - h / 2, ancla)
                    base = caja.y2
                else:
                    base = info['fondo'] + alto_cta
                    self.agregar_texto('cta', 'cta', self.c['cta'], xt, base, t['cta'], ancla)
                self.notas.append('el llamado no cabe junto al logo: va bajo las filas')
                info['fondo'] = base
        return info

    # ---------------------------------------------------------------- pie
    def preparar_pie(self, x0: float, x1: float) -> dict:
        """Mide logo y llamado; dice si el llamado cabe al lado del logo."""
        v = self.v
        comp = v['logo_composicion']
        ruta = marca.ruta_lockup(self.ctx.dir_lockups, self.ctx.esquema['lockups'], comp, 'claro')
        _, vw, vh = marca.leer_svg_oficial(ruta)
        alto = v['logo_altura_relativa'] * self.s
        ancho = alto * vw / vh
        minimo = self.ctx.reglas['lockup_ancho_minimo_px']
        if ancho < minimo:
            self.notas.append(f'logo agrandado a {minimo} px de ancho (mínimo del manual)')
            alto, ancho = alto * minimo / ancho, minimo
        cta = None
        if self.c.get('cta') and v['cta_visible'] and self.ctx.esquema['densidades'][v['densidad_texto']]['cta']:
            cta = self.medir('cta', self.preparar_texto('cta', self.c['cta']), self.t['cta'])
        boton = cta is not None and v['cta_estilo'] == 'boton'
        relleno = 2 * self.mod(v['cta_boton_relleno_h']) if boton else 0.0
        cabe = cta is None or ancho + 2 * self.medianil + cta['avance'] + relleno <= (x1 - x0)
        return {'alto': alto, 'ancho': ancho, 'cta': cta, 'cta_cabe': cabe, 'x0': x0, 'x1': x1, 'comp': comp}

    def alto_boton_cta(self) -> float:
        return self.medir('cta', 'H', self.t['cta'])['cap'] + 2 * self.mod(self.v['cta_boton_relleno_v'])

    def boton_cta(self, x: float, y_centro: float, anclaje: str) -> Rect:
        """Llamado como botón: bloque de acento con el texto en el color del fondo (cta_estilo: boton)."""
        v = self.v
        m = self.medir('cta', self.preparar_texto('cta', self.c['cta']), self.t['cta'])
        ph, pv = self.mod(v['cta_boton_relleno_h']), self.mod(v['cta_boton_relleno_v'])
        w, h = m['avance'] + 2 * ph, m['cap'] + 2 * pv
        bx = x if anclaje == 'start' else (x - w if anclaje == 'end' else x - w / 2)
        caja = Rect(bx, y_centro - h / 2, w, h)
        self.el.append({'tipo': 'boton', 'caja': caja, 'radio': self.ctx.reglas['radio_en_linea_px']})
        # cuenta como fondo al medir el contraste del texto que lleva encima
        self.velos.append({'rect': caja, 'color': self.rgba('cta_boton'), 'fijo': True, 'id': 'cta-boton'})
        self.agregar_texto('cta', 'cta', self.c['cta'], caja.x + w / 2, caja.y + pv + m['cap'], self.t['cta'],
                           'middle', 'cta_boton_texto')
        self.zonas['cta_boton'] = caja.a_dict()
        return caja

    def colocar_pie(self, p: dict, y2: float | None = None) -> Rect:
        v = self.v
        y = (self.caja.y2 if y2 is None else y2) - p['alto']
        izquierda = v['logo_posicion'] == 'inferior_izquierda'
        x = p['x0'] if izquierda else p['x1'] - p['ancho']
        self.logo = {'comp': p['comp'], 'x': x, 'y': y, 'alto': p['alto'], 'ancho': p['ancho']}
        if p['cta'] and p['cta_cabe'] and v['cta_estilo'] == 'boton':
            # centrado en la línea del logo
            self.boton_cta(p['x1'] if izquierda else p['x0'], y + p['alto'] / 2, 'end' if izquierda else 'start')
        elif p['cta'] and p['cta_cabe']:
            base = y + p['alto'] / 2 + p['cta']['cap'] / 2
            if izquierda:
                self.agregar_texto('cta', 'cta', self.c['cta'], p['x1'], base, self.t['cta'], 'end')
            else:
                self.agregar_texto('cta', 'cta', self.c['cta'], p['x0'], base, self.t['cta'], 'start')
        self.zonas['pie'] = Rect(p['x0'], y, p['x1'] - p['x0'], p['alto']).a_dict()
        return Rect(p['x0'], y, p['x1'] - p['x0'], p['alto'])

    def resolver_logo(self):
        """Elige la variante del lockup según el fondo real bajo el logo (Manual §02)."""
        lg = self.logo
        caja = Rect(lg['x'], lg['y'], lg['ancho'], lg['alto'])
        variante = self.v['logo_variante']
        candidatas = ['claro', 'oscuro'] if variante == 'auto' else [variante]
        mejor = None
        for cand in candidatas:
            ruta = marca.ruta_lockup(self.ctx.dir_lockups, self.ctx.esquema['lockups'], lg['comp'], cand)
            interior, vw, vh = marca.leer_svg_oficial(ruta)
            marcas_iso = {self.tema[t].upper() for t in ('--ub-mark-light', '--ub-mark-mid', '--ub-mark-shade')}
            primarios = {self.ctx.tokens[m]['--ub-primary'].upper() for m in ('claro', 'oscuro')}
            texto = sorted(marca.fills_de(interior) - marcas_iso - primarios)
            peor = min(self.contraste_en(caja, marca.color_rgba(f)) for f in texto) if texto else 0
            if mejor is None or peor > mejor['contraste']:
                mejor = {'variante': cand, 'ruta': ruta, 'interior': interior, 'vw': vw, 'vh': vh,
                         'contraste': peor, 'relleno_texto': texto}
        lg.update(mejor)
        lg['escala'] = lg['alto'] / mejor['vh']
        lg['caja'] = caja
        self.el.append({'tipo': 'logo'})

    # ---------------------------------------------------------------- decoración
    def trama(self, panel: Rect | None = None):
        """Retícula de puntos. Con trama_alcance: zona_texto queda dentro del panel de texto."""
        v = self.v
        if not v['trama_visible']:
            return
        inset = v['trama_inset'] * self.margen
        x0, y0, x1, y1 = inset, inset, self.W - inset, self.H - inset
        if v['trama_alcance'] == 'zona_texto' and panel is not None:
            # dentro del panel, a un medianil de los bordes que dan a la imagen
            m = self.medianil
            x0 = max(x0, panel.x + (m if panel.x > 0 else 0))
            y0 = max(y0, panel.y + (m if panel.y > 0 else 0))
            x1 = min(x1, panel.x2 - (m if panel.x2 < self.W else 0))
            y1 = min(y1, panel.y2 - (m if panel.y2 < self.H else 0))
        self.el.append({'tipo': 'trama', 'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                        'paso': self.mod(v['trama_paso']), 'r': v['trama_radio_rel'] * self.s,
                        'opacidad': v[f'trama_opacidad_{self.modo}'], 'color': 'trama'})

    def cruces_registro(self):
        v = self.v
        if not v['cruces_registro']:
            return
        inset = v['cruces_inset'] * self.margen
        tam = v['cruz_registro_tamano_rel'] * self.s
        for cx, cy in ((inset, inset), (self.W - inset, inset), (inset, self.H - inset), (self.W - inset, self.H - inset)):
            self.el.append({'tipo': 'cruz', 'cx': cx, 'cy': cy, 'tam': tam, 'color': 'acento', 'registro': True})

    def chip(self, ancla: Rect | None = None) -> Rect | None:
        """Chip EJEMPLO. Devuelve su caja para reservar espacio.

        `ancla` (proceso C) lo pone en la esquina de la zona de lectura, sobre el velo.
        """
        if not self.c.get('ejemplo'):
            return None
        v = self.v
        texto = self.preparar_texto('chip', self.c.get('chip', 'EJEMPLO'))
        m = self.medir('chip', texto, self.t['chip'])
        w = m['avance'] + 2 * self.mod(v['chip_relleno_h'])
        h = m['cap'] + 2 * self.mod(v['chip_relleno_v'])
        if ancla is not None:
            x2, y = ancla.x2, ancla.y
        elif v['chip_ancla'] == 'linea_cruces':
            inset = v['cruces_inset'] * self.margen
            x2, y = self.W - inset, inset - h / 2
        else:
            x2, y = self.caja.x2, self.caja.y
        caja = Rect(x2 - w, y, w, h)
        self.el.append({'tipo': 'chip_fondo', 'caja': caja, 'radio': self.ctx.reglas['radio_en_linea_px']})
        self.agregar_texto('chip', 'chip', texto, caja.x + w / 2, y + h / 2 + m['cap'] / 2, self.t['chip'], 'middle')
        self.zonas['chip'] = caja.a_dict()
        self.velos.append({'rect': caja, 'color': self.rgba('chip_fondo'), 'fijo': True, 'id': 'chip'})
        return caja

    # ---------------------------------------------------------------- ilustración
    def _leer_ilustracion(self):
        cfg = self.ctx.ilustraciones['wireframe_iso']
        ruta = self.ctx.marca / cfg['archivo']
        crudo = ruta.read_text(encoding='utf-8')
        m = re.search(r'<g id="wireframe-iso"[^>]*>(.*)</g>', crudo, flags=re.S)
        interior = m.group(1)
        xs, ys = [], []
        for d in re.findall(r' d="([^"]+)"', interior):
            pares = re.findall(r'(-?[\d.]+),(-?[\d.]+)', d)
            xs += [float(a) for a, _ in pares]
            ys += [float(b) for _, b in pares]
        for x1, y1, x2, y2 in re.findall(r'x1="(-?[\d.]+)" y1="(-?[\d.]+)" x2="(-?[\d.]+)" y2="(-?[\d.]+)"', interior):
            xs += [float(x1), float(x2)]
            ys += [float(y1), float(y2)]
        acento = marca.hex_de(self.rgba('acento'))
        interior = re.sub(r'stroke="#[0-9A-Fa-f]{6}"', f'stroke="{acento}"', interior)
        interior = re.sub(r'<(path|line) ', r'<\1 vector-effect="non-scaling-stroke" ', interior)
        return interior, (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)), ruta, cfg

    def ilustracion_en(self, zona: Rect):
        v = self.v
        interior, (bx, by, bw, bh), ruta, cfg = self._leer_ilustracion()
        if v['ilustracion_anclaje'] == 'libre':
            k = v['ilustracion_escala_libre'] / cfg['escala_nativa']
            cx, cy = v['ilustracion_centro_rel'][0] * self.W, v['ilustracion_centro_rel'][1] * self.H
            ox, oy = cfg['origen']
            tx, ty = cx - ox * k, cy - oy * k
        else:
            k = min(zona.w / bw, zona.h / bh) * v['ilustracion_escala']
            dw, dh = bw * k, bh * k
            al = v['ilustracion_alineacion']
            x = zona.x + (zona.w - dw) / 2 if al != 'inferior_derecha' else zona.x2 - dw
            y = zona.y + (zona.h - dh) / 2 if al == 'centro' else zona.y2 - dh
            tx, ty = x - bx * k, y - by * k
        caja = Rect(tx + bx * k, ty + by * k, bw * k, bh * k)
        self.el.append({'tipo': 'ilustracion', 'interior': interior, 'tx': tx, 'ty': ty, 'k': k,
                        'ruta': str(ruta), 'caja': caja})
        self.zonas['ilustracion'] = caja.a_dict()

    # ---------------------------------------------------------------- imagen
    def imagen_en(self, zona: Rect, radio: float):
        v = self.v
        ident = v['imagen_fuente']
        if ident not in self.ctx.catalogo:
            raise ValueError(f'imagen {ident!r} no está en imagenes.yaml')
        info = self.ctx.catalogo[ident]
        ruta = self.ctx.dir_mj / info['archivo']
        iw, ih = info['tamano_px']
        # con imagen_registro 'lienzo' la imagen se encuadra como si cubriera todo el lienzo y la
        # zona solo la recorta: entre presets del paso 3 la imagen no se mueve
        marco = Rect(0, 0, self.W, self.H) if v['imagen_registro'] == 'lienzo' else zona
        k = max(marco.w / iw, marco.h / ih)
        dw, dh = iw * k, ih * k
        fx, fy = v['imagen_foco']
        x = min(marco.x, max(marco.x2 - dw, marco.x + marco.w / 2 - fx * dw))
        y = min(marco.y, max(marco.y2 - dh, marco.y + marco.h / 2 - fy * dh))
        self.imagen = {'id': ident, 'ruta': ruta, 'x': x, 'y': y, 'w': dw, 'h': dh, 'zona': zona,
                       'radio': radio, 'info': info, 'escala': k}
        self.el.append({'tipo': 'imagen'})
        self.zonas['imagen'] = zona.a_dict()
        self._raster_fondo()

    def _raster_fondo(self):
        base = np.empty((self.H, self.W, 3), dtype=float)
        base[:] = marca.color_rgba(self.colores['fondo'])[:3]
        im = self.imagen
        if im:
            w, h = max(1, round(im['w'])), max(1, round(im['h']))
            arr = np.asarray(Image.open(im['ruta']).convert('RGB').resize((w, h), Image.Resampling.LANCZOS),
                             dtype=float)
            z = im['zona']
            x0, y0 = max(0, round(z.x)), max(0, round(z.y))
            x1, y1 = min(self.W, round(z.x2)), min(self.H, round(z.y2))
            ox, oy = round(im['x']), round(im['y'])
            base[y0:y1, x0:x1] = arr[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        self.fondo = base

    def muestra(self, caja: Rect, velos: list | None = None) -> np.ndarray:
        if self.fondo is None:
            self._raster_fondo()
        x0, y0 = max(0, int(caja.x)), max(0, int(caja.y))
        x1, y1 = min(self.W, int(math.ceil(caja.x2))), min(self.H, int(math.ceil(caja.y2)))
        if x1 <= x0 or y1 <= y0:
            return np.empty((0, 3))
        reg = self.fondo[y0:y1, x0:x1].copy()
        for velo in (self.velos if velos is None else velos):
            r = velo['rect']
            a0, b0 = max(x0, int(r.x)), max(y0, int(r.y))
            a1, b1 = min(x1, int(math.ceil(r.x2))), min(y1, int(math.ceil(r.y2)))
            if a1 <= a0 or b1 <= b0:
                continue
            *rgb, alfa = velo['color']
            alfa = velo.get('opacidad', alfa) if not velo.get('fijo') else alfa
            sub = reg[b0 - y0:b1 - y0, a0 - x0:a1 - x0]
            reg[b0 - y0:b1 - y0, a0 - x0:a1 - x0] = alfa * np.array(rgb) + (1 - alfa) * sub
        return reg.reshape(-1, 3)

    def contraste_en(self, caja: Rect, rgb_texto, velos: list | None = None) -> float:
        px = self.muestra(caja, velos)
        if not len(px):
            return 0.0
        return float(np.percentile(contrastes(rgb_texto, px), self.PERCENTIL_CONTRASTE))

    def color_texto(self, el: dict):
        return self.rgb_opaco(el['color'])

    # ---------------------------------------------------------------- texto sobre imagen
    def es_grande(self, el: dict) -> bool:
        """Texto grande según WCAG: 18 pt, o 14 pt desde peso 600 (en px CSS de la vista)."""
        css = el['tamano'] / self.px_por_css
        umbral = self.v['texto_grande_negrita_css'] if el['peso'] >= 600 else self.v['texto_grande_css']
        return css >= umbral - 0.01

    def sobre_imagen(self, el: dict) -> bool:
        return (self.imagen is not None and el['rol'] != 'chip'
                and el['caja'].interseca(self.imagen['zona']))

    def contraste_objetivo(self, el: dict) -> float:
        """4,5:1 (UB-3) para todo texto; contraste_sobre_imagen para el texto chico sobre imagen."""
        minimo = self.ctx.reglas['contraste_texto_minimo']
        if self.sobre_imagen(el) and not self.es_grande(el):
            return max(minimo, self.v['contraste_sobre_imagen'])
        return minimo

    def aplicar_colores_sobre_imagen(self):
        """El texto chico sobre imagen pasa a los tokens de texto más claros (si el pack lo pide)."""
        if self.v['colores_sobre_imagen'] != 'claros' or self.imagen is None:
            return
        mapa = self.ctx.esquema['roles_color_sobre_imagen'][self.modo]
        cambios = {}
        for e in self.el:
            if e['tipo'] == 'texto' and self.sobre_imagen(e) and not self.es_grande(e):
                nuevo = mapa.get(e['color'])
                if nuevo and nuevo != e['color']:
                    cambios.setdefault(f"{e['color']} -> {nuevo}", []).append(e['id'])
                    e['color'] = nuevo
        for cambio, ids in cambios.items():
            self.notas.append(f'texto chico sobre imagen, {cambio}: {", ".join(ids)}')

    def velo(self, rect: Rect, ident: str, grupo: str | None = None):
        """Velo plano. Los velos de un mismo grupo comparten opacidad y se pintan como una sola forma."""
        rgb = marca.color_rgba(self.colores['velo'])[:3]
        self.velos.append({'rect': rect, 'color': (*rgb, self.v['velo_opacidad']),
                           'opacidad': self.v['velo_opacidad'], 'id': ident, 'grupo': grupo or ident})
        self.el.append({'tipo': 'velo', 'id': ident})

    def ajustar_velos(self):
        """Sube cada velo (o grupo de velos) lo justo para que cada texto sobre él llegue a su objetivo."""
        if not self.v['velo_auto']:
            return
        tope = self.ctx.esquema['parametros']['velo_opacidad']['rango'][1]
        grupos: dict[str, list] = {}
        for vl in self.velos:
            if not vl.get('fijo'):
                grupos.setdefault(vl['grupo'], []).append(vl)
        minimo = self.ctx.reglas['contraste_texto_minimo']
        for grupo, velos in grupos.items():
            # (caja, color, objetivo) de cada texto sobre el velo
            medidas = [(e['caja'], self.color_texto(e), self.contraste_objetivo(e)) for e in self.el
                       if e['tipo'] == 'texto' and any(e['caja'].interseca(vl['rect']) for vl in velos)]
            if self.logo is not None:
                # el logotipo cuenta como texto chico: su «Umbral» va en la tinta del tema
                caja = Rect(self.logo['x'], self.logo['y'], self.logo['ancho'], self.logo['alto'])
                if any(caja.interseca(vl['rect']) for vl in velos):
                    sobre = self.imagen is not None and caja.interseca(self.imagen['zona'])
                    medidas.append((caja, self.rgb_opaco('tinta'),
                                    max(minimo, self.v['contraste_sobre_imagen']) if sobre else minimo))
            if not medidas:
                continue
            objetivos = sorted({m[2] for m in medidas})

            def holgura(alfa):
                for vl in velos:
                    vl['opacidad'] = alfa
                return min(self.contraste_en(caja, rgb) / obj for caja, rgb, obj in medidas)

            inicial = velos[0]['opacidad']
            if holgura(inicial) >= 1:
                continue
            lo, hi = inicial, tope
            if holgura(hi) < 1:
                self.notas.append(f'velo {grupo}: ni con {hi:.2f} se alcanza el contraste objetivo')
                continue
            for _ in range(12):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if holgura(mid) < 1 else (lo, mid)
            final = round(math.ceil(hi * 100) / 100, 2)
            holgura(final)
            self.notas.append(f'velo {grupo}: opacidad {inicial:.2f} -> {final:.2f} para cumplir '
                              f'{" y ".join(f"{o:g}:1" for o in objetivos)}')

    def zona_libre_auto(self, fraccion: float) -> tuple[str, dict]:
        """La franja de la imagen con menos detalle (gradiente medio de luminancia)."""
        lum = luminancias(self.fondo)
        grad = np.zeros_like(lum)
        grad[:, 1:] += np.abs(np.diff(lum, axis=1))
        grad[1:, :] += np.abs(np.diff(lum, axis=0))
        fw, fh = round(self.W * fraccion), round(self.H * fraccion)
        regiones = {'izquierda': grad[:, :fw], 'derecha': grad[:, self.W - fw:],
                    'superior': grad[:fh, :], 'inferior': grad[self.H - fh:, :]}
        puntajes = {k: round(float(r.mean()) * 1000, 3) for k, r in regiones.items()}
        return min(puntajes, key=puntajes.get), puntajes

    # ---------------------------------------------------------------- procesos
    def componer(self):
        self.preparar_grilla()
        self.preparar_tamanos()
        self.el.append({'tipo': 'fondo'})
        getattr(self, f'_proceso_{self.v["proceso"]}')()
        self.aplicar_colores_sobre_imagen()
        if self.v['velo_auto']:
            self.ajustar_velos()
        self.resolver_logo()
        self._ordenar_capas()

    def _ordenar_capas(self):
        orden = ['fondo', 'imagen', 'velo', 'trama', 'cruz', 'ilustracion', 'linea', 'boton', 'texto', 'logo',
                 'chip_fondo']
        def clave(e):
            if e['tipo'] == 'texto' and e['id'] == 'chip':
                return len(orden) + 1
            return orden.index(e['tipo'])
        self.el.sort(key=clave)

    def _zona_ilustracion_A(self, c0: int, c1: int, f_texto_fin: int, f_titulo_fin: int, reserva: Rect | None):
        z = self.v['ilustracion_zona']
        pie = self.M - 1
        if z == 'ninguna':
            return None
        if z == 'derecha':
            r = self.celdas(c1, self.N, 0, pie) if c1 < self.N else None
        elif z == 'inferior':
            r = self.celdas(0, self.N, f_texto_fin, pie) if f_texto_fin < pie else None
        else:  # derecha_inferior o auto
            r = self.celdas(c1, self.N, f_titulo_fin, pie) if c1 < self.N and f_titulo_fin < pie else None
        if r is not None and reserva is not None and r.interseca(reserva):
            corte = reserva.y2 + self.medianil
            r = Rect(r.x, corte, r.w, r.y2 - corte)
        return r

    def _fila_tras(self, y: float) -> int:
        return next((j for j in range(self.M) if self.y_fil(j) >= y + self.medianil - 0.5), self.M - 1)

    def _columnas_titulo(self, c0: int, ct: int) -> int:
        v = self.v
        cols = v['columnas_titulo'] or ct
        if cols > ct and v['ilustracion_zona'] == 'derecha':
            self.notas.append('columnas_titulo limitado a columnas_texto: la ilustración ocupa toda la derecha')
            cols = ct
        if cols > ct and v['filas_ubicacion'] == 'columna_derecha':
            self.notas.append('columnas_titulo limitado a columnas_texto: las filas ocupan la derecha')
            cols = ct
        return min(cols, self.N - c0)

    def _proceso_A_grilla(self):
        """La grilla manda: zonas por celdas, el contenido se acomoda."""
        v = self.v
        ct = min(v['columnas_texto'], self.N)
        c0 = 0 if v['alineacion'] == 'izquierda' else (self.N - ct) // 2
        zona = self.celdas(c0, c0 + ct, 0, self.M - 1)
        self.zonas['texto'] = zona.a_dict()
        reserva = self.chip()
        self.trama()
        self.cruces_registro()
        pie = self.preparar_pie(self.caja.x, self.caja.x2)
        cols_tit = self._columnas_titulo(c0, ct)
        ancho_cabecera = self.celdas(c0, c0 + cols_tit, 0, 1).w
        tam = self.tamano_titulo(ancho_cabecera)
        ubic = v['filas_ubicacion']
        zona_filas = None
        if ubic == 'columna_derecha':
            if c0 + ct < self.N:
                zona_filas = self.celdas(c0 + ct, self.N, 0, self.M - 1)
            else:
                self.notas.append('no quedan columnas a la derecha: las filas van bajo el título')
                ubic = 'bajo_titulo'
        info = self.pila(zona, tam, ubic, filas_a_grilla=True, cta_en_pila=not pie['cta_cabe'],
                         zona_filas=zona_filas, ancho_cabecera=ancho_cabecera)
        self.colocar_pie(pie)
        fin_texto = max(info['fondo'], info.get('fondo_filas') or 0)
        # la cabecera (título y subtítulo) puede ocupar más columnas que el resto: la celda
        # de la ilustración empieza en la fila de grilla siguiente a la cabecera
        zona_ilu = self._zona_ilustracion_A(c0, c0 + ct, self._fila_tras(fin_texto),
                                            self._fila_tras(info['fondo_cabecera']), reserva)
        self._llenar_zona(zona_ilu)

    def _llenar_zona(self, zona: Rect | None):
        if zona is None or zona.w <= 0 or zona.h <= 0:
            return
        v = self.v
        minimo = v['ilustracion_minimo_rel'] * self.s
        if min(zona.w, zona.h) < minimo and not v['imagen_fuente']:
            self.notas.append(f'sin ilustración: la zona libre ({zona.w:.0f}×{zona.h:.0f}) es menor que '
                              f'{minimo:.0f} px')
            return
        if v['imagen_encaje'] in ('caja_alineada_grilla', 'sangrado_lateral') and v['imagen_fuente']:
            radio = v['imagen_radio']
            if v['imagen_encaje'] == 'sangrado_lateral':
                # sangra solo hacia el costado más cercano; arriba y abajo respeta la grilla
                if zona.x + zona.w / 2 > self.W / 2:
                    zona = Rect(zona.x, zona.y, self.W - zona.x, zona.h)
                else:
                    zona = Rect(0, zona.y, zona.x2, zona.h)
                radio = 0
            self.imagen_en(zona, radio)
        elif v['ilustracion_zona'] != 'ninguna':
            self.ilustracion_en(zona)

    def _proceso_B_contenido(self):
        """El contenido manda: jerarquía y medidas primero, la grilla se deriva."""
        v = self.v
        reserva = self.chip()
        self.trama()
        self.cruces_registro()
        ancho_max = self.caja.w * v['texto_ancho_max_relativo']
        tam = self.tamano_titulo(ancho_max)
        filas = self.filas_activas()
        dens = self.ctx.esquema['densidades'][v['densidad_texto']]
        anchos_texto = [self.medir('titulo', self.preparar_texto('titulo', l), tam)['avance'] for l in self.c['titulo']]
        for rol in ('kicker', 'subtitulo', 'cuerpo'):
            if self.c.get(rol) and dens[rol]:
                anchos_texto.append(self.medir(rol, self.preparar_texto(rol, self.c[rol]), self.t[rol])['avance'])
        ancho_filas = self.medidas_filas(filas)['ancho_min'] if filas else 0
        ubic = v['filas_ubicacion']
        en_columna = ubic == 'columna_derecha' and bool(filas)
        paso = self.col_w + self.medianil
        cols = lambda ancho: math.ceil((ancho + self.medianil) / paso - 1e-6)
        if en_columna:
            # primero las columnas que las filas necesitan; el título se ajusta a lo que queda
            k_filas = min(self.N - 2, cols(ancho_filas))
            k = max(2, min(self.N - k_filas, cols(max(anchos_texto))))
            ancho_txt = self.x_col(k - 1) + self.col_w - self.caja.x
            if max(anchos_texto[:len(self.c['titulo'])]) > ancho_txt * v['titulo_ancho_max']:
                tam = self.tamano_titulo(ancho_txt)
            self.notas.append(f'grilla derivada: filas {self.N - k} columnas ({ancho_filas:.0f} px), texto {k}')
        else:
            natural = max(anchos_texto + [ancho_filas])
            k = max(2, min(self.N, cols(natural)))
            self.notas.append(f'grilla derivada: el texto mide {natural:.0f} px y toma {k} de {self.N} columnas')
        pie = self.preparar_pie(self.caja.x, self.caja.x2)
        fondo_util = self.caja.y2 - pie['alto'] - self.mod(v['espacio_pie'])
        zona = Rect(self.caja.x, self.caja.y, self.x_col(k - 1) + self.col_w - self.caja.x, fondo_util - self.caja.y)
        self.zonas['texto'] = zona.a_dict()
        zona_filas = None
        if en_columna:
            zona_filas = Rect(self.x_col(k), self.caja.y, self.caja.x2 - self.x_col(k), fondo_util - self.caja.y)
        info = self.pila(zona, tam, ubic if filas else 'bajo_titulo', cta_en_pila=not pie['cta_cabe'],
                         zona_filas=zona_filas)
        self.colocar_pie(pie)
        # el espacio que sobra: la zona libre más grande (derecha, debajo o entre título y filas al pie)
        gap = self.mod(v['espacio_subtitulo_filas'])
        candidatas = {}
        if not en_columna and k < self.N:
            tope_der = (reserva.y2 + self.medianil) if reserva else self.caja.y
            candidatas['derecha'] = Rect(self.x_col(k), tope_der, self.caja.x2 - self.x_col(k), fondo_util - tope_der)
        fin = max(info['fondo'], info.get('fondo_filas') or 0)
        if fondo_util - (fin + gap) > 0:
            candidatas['debajo'] = Rect(self.caja.x, fin + gap, self.caja.w, fondo_util - fin - gap)
        if info['filas'] is not None and ubic == 'al_pie':
            alto = info['filas'].y - gap - (info['fondo_pila'] + gap)
            if alto > 0:
                candidatas['entre título y filas'] = Rect(self.caja.x, info['fondo_pila'] + gap, self.caja.w, alto)
        pedida = {'derecha': 'derecha', 'inferior': 'debajo'}.get(v['ilustracion_zona'])
        if v['ilustracion_zona'] == 'ninguna':
            return
        if pedida and pedida in candidatas:
            nombre = pedida
        elif candidatas:
            nombre = max(candidatas, key=lambda n: min(candidatas[n].w, candidatas[n].h))
        else:
            return
        self.notas.append(f'zona libre para la ilustración: {nombre}')
        self._llenar_zona(candidatas[nombre])

    def _proceso_C_imagen(self):
        """La imagen manda: su zona con menos detalle recibe el texto, protegido por un velo plano."""
        v = self.v
        encaje = v['imagen_encaje']
        if v['division'] != 'zona_libre':
            preset = self.ctx.esquema['divisiones'][v['division']]
            if encaje == 'fondo_completo_con_velo':
                if not v['imagen_fuente']:
                    raise ValueError('fondo_completo_con_velo necesita imagen_fuente')
                self.imagen_en(Rect(0, 0, self.W, self.H), 0)
            partes = getattr(self, f"_division_{preset['tipo']}")(preset)
            self._llenar_parte(partes)
            return
        if not v['imagen_fuente'] or encaje == 'sin_imagen':
            raise ValueError('el proceso C necesita imagen_fuente e imagen_encaje')
        frac = v['zona_libre_fraccion']
        if encaje == 'fondo_completo_con_velo':
            self.imagen_en(Rect(0, 0, self.W, self.H), 0)
            lado = v['zona_libre']
            if lado == 'auto':
                lado, puntajes = self.zona_libre_auto(frac)
                self.notas.append(f'zona libre automática: {lado} (detalle medio {puntajes})')
        else:
            lado = v['zona_libre'] if v['zona_libre'] != 'auto' else 'izquierda'
        k = max(2, min(self.N - 1, round(frac * self.N)))
        if lado in ('izquierda', 'derecha'):
            c0 = 0 if lado == 'izquierda' else self.N - k
            x0, x1 = self.x_col(c0), self.x_col(c0 + k - 1) + self.col_w
        else:
            x0, x1 = self.caja.x, self.caja.x2
        self.trama()
        self.cruces_registro()
        pie = self.preparar_pie(x0, x1)
        fondo_util = self.caja.y2 - pie['alto'] - self.mod(v['espacio_pie'])
        if lado == 'superior':
            zona = Rect(x0, self.caja.y, x1 - x0, frac * self.H - self.caja.y)
        elif lado == 'inferior':
            tope = (1 - frac) * self.H
            zona = Rect(x0, tope, x1 - x0, fondo_util - tope)
        else:
            zona = Rect(x0, self.caja.y, x1 - x0, fondo_util - self.caja.y)
        # el chip va en la esquina de la zona de lectura, para quedar sobre el velo
        reserva = self.chip(ancla=zona)
        if reserva is not None:
            corte = reserva.y2 + self.medianil
            zona = Rect(zona.x, corte, zona.w, zona.y2 - corte)
        self.zonas['texto'] = zona.a_dict()
        tam = self.tamano_titulo(zona.w)
        ubic = v['filas_ubicacion'] if v['filas_ubicacion'] != 'columna_derecha' else 'bajo_titulo'
        info = self.pila(zona, tam, ubic, anclar_abajo=lado == 'inferior', cta_en_pila=not pie['cta_cabe'])
        self.colocar_pie(pie)
        if encaje == 'sangrado_lateral':
            if lado == 'izquierda':
                self.imagen_en(Rect(x1 + self.medianil, 0, self.W - x1 - self.medianil, self.H), 0)
            elif lado == 'derecha':
                self.imagen_en(Rect(0, 0, x0 - self.medianil, self.H), 0)
            else:
                raise ValueError('sangrado_lateral necesita zona_libre izquierda o derecha')
            return
        # zona de lectura protegida: franja alineada a la grilla que sangra al borde y
        # cubre todo el texto que de verdad se compuso (no solo la franja pedida)
        if v['velo_alcance'] == 'completo':
            self.velo(Rect(0, 0, self.W, self.H), 'velo-completo')
            return
        m = self.medianil
        arriba = min(zona.y, info['tope'], reserva.y if reserva else zona.y) - m
        abajo = max(zona.y2, info['fondo']) + m
        pie_y = self.caja.y2 - pie['alto'] - m
        if lado == 'izquierda':
            self.velo(Rect(0, 0, x1 + m, self.H), 'velo-lectura')
        elif lado == 'derecha':
            self.velo(Rect(x0 - m, 0, self.W - x0 + m, self.H), 'velo-lectura')
        elif lado == 'superior':
            self.velo(Rect(0, 0, self.W, abajo), 'velo-lectura')
            if pie_y > abajo:
                self.velo(Rect(0, pie_y, self.W, self.H - pie_y), 'velo-pie')
        else:
            self.velo(Rect(0, arriba, self.W, self.H - arriba), 'velo-lectura')

    # ---------------------------------------------------------------- paso 1 · divisiones
    def _columnas_de(self, fraccion: float) -> int:
        return max(2, min(self.N - 2, round(fraccion * self.N)))

    def _filas_de(self, fraccion: float) -> int:
        return max(1, min(self.M - 1, round(fraccion * self.M)))

    def _titulo_que_cabe(self, zona: Rect, ubicacion_filas: str, cta_en_pila: bool = False,
                         zona_filas: Rect | None = None) -> float:
        """Título que cabe en el ancho y en el alto de la zona (el alto lo fija la división)."""
        tam = self.tamano_titulo(zona.w)

        def alto(t):
            return self.pila(zona, t, ubicacion_filas, cta_en_pila=cta_en_pila, zona_filas=zona_filas,
                             solo_medir=True)

        if alto(tam) <= zona.h:
            return tam
        lo, hi = tam * 0.25, tam
        for _ in range(14):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if alto(mid) <= zona.h else (lo, mid)
        nuevo = math.floor(lo * 10) / 10
        self.notas.append(f'título reducido de {tam:.0f} a {nuevo:.0f} px para caber en {zona.h:.0f} px de alto')
        return nuevo

    def _division_columna(self, p: dict):
        """Texto en k de N columnas y la imagen en el resto (la 12° de G01 es la mitad izquierda)."""
        v, m = self.v, self.medianil
        k = self._columnas_de(v['division_fraccion'] or p['fraccion'])
        izquierda = p['lado'] == 'izquierda'
        c0 = 0 if izquierda else self.N - k
        x0, x1 = self.x_col(c0), self.x_col(c0 + k - 1) + self.col_w
        self.notas.append(f"división {v['division']}: texto en {k} de {self.N} columnas")
        self.trama(Rect(0, 0, x1 + m, self.H) if izquierda else None)
        self.cruces_registro()
        pie = self.preparar_pie(x0, x1)
        fondo_util = self.caja.y2 - pie['alto'] - self.mod(v['espacio_pie'])
        zona = Rect(x0, self.caja.y, x1 - x0, fondo_util - self.caja.y)
        reserva = self.chip(ancla=zona)
        if reserva is not None:
            zona = Rect(zona.x, reserva.y2 + m, zona.w, zona.y2 - reserva.y2 - m)
        self.zonas['texto'] = zona.a_dict()
        ubic = v['filas_ubicacion'] if v['filas_ubicacion'] != 'columna_derecha' else 'bajo_titulo'
        abajo = v['pila_anclaje'] == 'abajo'
        if abajo and ubic == 'al_pie':
            ubic = 'bajo_titulo'
            self.notas.append('pila apoyada abajo: las filas van bajo el título')
        tam = self._titulo_que_cabe(zona, ubic, cta_en_pila=not pie['cta_cabe'])
        self.pila(zona, tam, ubic, cta_en_pila=not pie['cta_cabe'], anclar_abajo=abajo)
        self.colocar_pie(pie)
        con_velo = v['imagen_encaje'] == 'fondo_completo_con_velo'
        if izquierda:
            if con_velo:
                self.velo(Rect(0, 0, x1 + m, self.H), 'velo-lectura')
            xi = x1 + m
            return {'sangre': Rect(xi, 0, self.W - xi, self.H),
                    'grilla': Rect(xi, self.caja.y, self.caja.x2 - xi, self.caja.h)}
        if con_velo:
            self.velo(Rect(x0 - m, 0, self.W - x0 + m, self.H), 'velo-lectura')
        xf = x0 - m
        return {'sangre': Rect(0, 0, xf, self.H),
                'grilla': Rect(self.caja.x, self.caja.y, xf - self.caja.x, self.caja.h)}

    def _division_banda(self, p: dict):
        """Imagen arriba y banda de texto abajo a todo el ancho: cabecera a la izquierda, datos a la derecha."""
        v, m = self.v, self.medianil
        n = self._filas_de(v['division_fraccion'] or p['fraccion'])
        superior = p.get('lado') == 'superior'
        if superior:
            # texto en las n filas de arriba, con el pie al fondo de la banda; la imagen debajo
            corte = self.y_fil(n)
            tope, panel, y_pie = self.caja.y, Rect(0, 0, self.W, corte), corte - m
        else:
            j = self.M - n                  # primera fila de grilla de la banda
            borde, tope = self.y_fil(j) - m, self.y_fil(j)
            panel, y_pie = Rect(0, borde, self.W, self.H - borde), self.caja.y2
        apilada = p.get('filas') == 'debajo'    # formatos verticales: los datos van bajo el título
        self.trama(panel)
        self.cruces_registro()
        pie = self.preparar_pie(self.caja.x, self.caja.x2)
        fondo_util = y_pie - pie['alto'] - self.mod(v['espacio_pie'])
        if apilada:
            self.notas.append(f"división {v['division']}: texto en las {n} filas de "
                              f"{'arriba' if superior else 'abajo'} ({n} de {self.M}), datos bajo el título")
            zona, zona_filas = Rect(self.caja.x, tope, self.caja.w, fondo_util - tope), None
            ubic = v['filas_ubicacion'] if v['filas_ubicacion'] in ('bajo_titulo', 'al_pie') else 'bajo_titulo'
        else:
            kc = self._columnas_de(p['fraccion_cabecera'])
            self.notas.append(f"división banda: texto en las {n} filas de abajo ({n} de {self.M}); cabecera en "
                              f"{kc} de {self.N} columnas y datos en {self.N - kc}")
            x_filas = self.x_col(kc)
            zona = Rect(self.caja.x, tope, self.x_col(kc - 1) + self.col_w - self.caja.x, fondo_util - tope)
            zona_filas = Rect(x_filas, tope, self.caja.x2 - x_filas, fondo_util - tope)
            ubic = 'columna_derecha'
        self.chip(ancla=Rect(self.caja.x, tope, self.caja.w, zona.h))
        self.zonas['texto'] = zona.a_dict()
        tam = self._titulo_que_cabe(zona, ubic, cta_en_pila=not pie['cta_cabe'], zona_filas=zona_filas)
        self.pila(zona, tam, ubic, cta_en_pila=not pie['cta_cabe'], zona_filas=zona_filas)
        self.colocar_pie(pie, y_pie)
        if v['imagen_encaje'] == 'fondo_completo_con_velo':
            self.velo(panel, 'velo-lectura')
        if superior:
            return {'sangre': Rect(0, corte, self.W, self.H - corte),
                    'grilla': Rect(self.caja.x, corte, self.caja.w, self.caja.y2 - corte)}
        return {'sangre': Rect(0, 0, self.W, borde),
                'grilla': Rect(self.caja.x, self.caja.y, self.caja.w, borde - self.caja.y)}

    def _division_ele(self, p: dict):
        """Cabecera arriba a todo el ancho y datos en la columna izquierda; la imagen queda en la esquina."""
        v, m = self.v, self.medianil
        n = self._filas_de(v['division_fraccion'] or p['fraccion_banda'])
        corte = self.y_fil(n)               # línea de grilla donde termina la banda y empieza la columna
        k = self._columnas_de(p['fraccion_columna'])
        x1 = self.x_col(k - 1) + self.col_w
        self.notas.append(f"división ele: cabecera en las {n} filas de arriba ({n} de {self.M}); datos en "
                          f"{k} de {self.N} columnas")
        self.trama()
        self.cruces_registro()
        cab = Rect(self.caja.x, self.caja.y, self.caja.w, corte - self.mod(v['espacio_subtitulo_filas']) - self.caja.y)
        self.chip(ancla=cab)
        self.zonas['texto'] = cab.a_dict()
        tam = self._titulo_que_cabe(cab, 'aparte')
        self.pila(cab, tam, 'aparte')
        pie = self.preparar_pie(self.caja.x, x1)
        filas = self.filas_activas()
        fin = self.bloque_filas(filas, self.caja.x, corte, x1 - self.caja.x) if filas else corte
        if pie['cta'] and not pie['cta_cabe']:
            base = fin + self.mod(v['espacio_filas_cuerpo']) + pie['cta']['cap']
            self.agregar_texto('cta', 'cta', self.c['cta'], self.caja.x, base, self.t['cta'])
            fin = base
        self.colocar_pie(pie)
        if fin > self.caja.y2 - pie['alto'] - self.mod(v['espacio_pie']) + 0.5:
            self.notas.append('ele: los datos no caben sobre el pie')
        if v['imagen_encaje'] == 'fondo_completo_con_velo':
            self.velo(Rect(0, 0, self.W, corte), 'velo-banda', grupo='velo-lectura')
            self.velo(Rect(0, corte, x1 + m, self.H - corte), 'velo-columna', grupo='velo-lectura')
        xi = x1 + m
        return {'sangre': Rect(xi, corte, self.W - xi, self.H - corte),
                'grilla': Rect(xi, corte, self.caja.x2 - xi, self.caja.y2 - corte)}

    def _llenar_parte(self, partes: dict):
        """Paso 3 · la imagen o la ilustración en la parte que dejó libre la división."""
        v = self.v
        encaje = v['imagen_encaje']
        if encaje == 'fondo_completo_con_velo':
            return                                   # ya está a sangre, bajo el velo
        if encaje in ('sangrado_lateral', 'caja_alineada_grilla'):
            if not v['imagen_fuente']:
                raise ValueError(f'{encaje} necesita imagen_fuente')
            if encaje == 'sangrado_lateral':
                self.imagen_en(partes['sangre'], 0)
            else:
                self.imagen_en(partes['grilla'], v['imagen_radio'])
            self.notas.append(f'imagen {encaje} en la parte libre de la división')
        elif v['ilustracion_zona'] != 'ninguna':
            self.ilustracion_en(partes['grilla'])
            self.notas.append('sin imagen: la ilustración vectorial ocupa la parte libre de la división')

    def _proceso_libre(self):
        """Posiciones sueltas como la v2: sirve para regenerarla desde un pack."""
        v = self.v
        self.chip()
        self.trama()
        self.cruces_registro()
        pie = self.preparar_pie(self.caja.x, self.caja.x2)
        tam = self.tamano_titulo(self.caja.w)
        self.pila(self.caja, tam, v['filas_ubicacion'], ancho_filas=v['filas_ancho_relativo'] * self.W)
        self.colocar_pie(pie)
        if v['ilustracion_zona'] != 'ninguna':
            self.ilustracion_en(self.caja)

    # ---------------------------------------------------------------- verificación
    def verificar(self, svg: str) -> list[dict]:
        r = self.ctx.reglas
        res = []

        def regla(nombre, ok, detalle, clase='ub3'):
            res.append({'regla': nombre, 'ok': bool(ok), 'detalle': detalle, 'clase': clase})

        textos = [e for e in self.el if e['tipo'] == 'texto']
        familias = sorted({e['familia'] for e in textos})
        regla('tipografias', set(familias) <= set(r['tipografias']), f'familias usadas: {familias}')
        usadas = {f"{e['familia']}|{e['peso']}" for e in textos}
        faltan = sorted(usadas - self.nav.caras_cargadas)
        regla('fuentes_cargadas', not faltan, 'todas las caras cargaron' if not faltan else f'sin cargar: {faltan}')
        turq = self.ctx.tokens['claro']['--ub-primary'].upper()
        malas = []
        for e in textos:
            hexa = marca.hex_de(self.color_texto(e)).upper()
            fondo = self.muestra(e['caja'])
            claro = len(fondo) and float(np.median(luminancias(fondo))) > 0.4
            if hexa == turq and claro:
                malas.append(e['id'])
        regla('turquesa_texto_sobre_claro', not malas, 'ninguno' if not malas else f'textos: {malas}')
        regla('sin_degradados', 'Gradient' not in svg, 'sin <linearGradient>/<radialGradient>; velos planos')
        espacios = {'margen': self.margen, 'margen_inferior': self.margen_inf, 'medianil': self.medianil,
                    'modulo': self.modulo}
        malos = {k: v for k, v in espacios.items() if v % r['espaciado_multiplo_px']}
        regla('espaciado_multiplo_4', not malos, f'{espacios}')
        lg = self.logo
        ok_logo = Path(lg['ruta']).parent.resolve() == self.ctx.dir_lockups.resolve()
        regla('lockup_oficial', ok_logo, f"{Path(lg['ruta']).name}")
        regla('lockup_ancho_minimo', lg['ancho'] >= r['lockup_ancho_minimo_px'] - 0.01,
              f"{lg['ancho']:.0f} px (mínimo {r['lockup_ancho_minimo_px']})")
        fp = self.v['fondo_portada']
        regla('fondo_portada', (not fp) or self.v['formato'] in r['fondo_portada_solo_en'],
              'no usa --ub-bg-cover' if not fp else f"usa --ub-bg-cover en {self.v['formato']}")
        regla('sin_negro_puro', marca.hex_de(self.rgba('fondo')).upper() != '#000000', self.colores['fondo'])
        dominios = [d for e in textos for d in re.findall(r'umbralbim\.[a-z]+', e['texto'].lower())]
        regla('dominio', all(d == r['dominio'] for d in dominios), f'{sorted(set(dominios)) or "sin dominio"}')
        minimo = r['contraste_texto_minimo']
        peores, detalle = [], {}
        for e in textos:
            cr = self.contraste_en(e['caja'], self.color_texto(e))
            detalle[e['id']] = round(cr, 2)
            if cr < minimo:
                peores.append(f"{e['id']} {cr:.2f}:1")
        self.contrastes = detalle
        regla('contraste_texto', not peores,
              f'mínimo medido {min(detalle.values()):.2f}:1 (p{self.PERCENTIL_CONTRASTE} del fondo real)'
              if not peores else f'bajo {minimo}:1: {peores}')
        chicos = [e for e in textos if self.sobre_imagen(e) and not self.es_grande(e)]
        if chicos:
            objetivo = self.contraste_objetivo(chicos[0])
            bajos = [f"{e['id']} {detalle[e['id']]:.2f}:1" for e in chicos if detalle[e['id']] < objetivo - 1e-9]
            regla('contraste_sobre_imagen', not bajos,
                  f"textos chicos sobre imagen: mínimo {min(detalle[e['id']] for e in chicos):.2f}:1 "
                  f"(objetivo {objetivo:g}:1)" if not bajos else f'bajo {objetivo:g}:1: {bajos}', 'calidad')
        regla('contraste_logo', lg['contraste'] >= minimo,
              f"«Umbral» {lg['relleno_texto']} sobre el fondo: {lg['contraste']:.2f}:1 (variante {lg['variante']})")
        radios_ok = (self.imagen is None or self.imagen['radio'] in (0, r['radio_bloque_px']))
        regla('radios', radios_ok, f"chip {r['radio_en_linea_px']} px; imagen "
                                   f"{self.imagen['radio'] if self.imagen else '-'} px")
        # calidad (no son reglas UB-3)
        min_css = min(e['tamano'] for e in textos if e['rol'] != 'chip') / self.px_por_css
        regla('texto_minimo_movil', min_css >= self.v['texto_minimo_css'] - 0.05,
              f'texto más chico: {min_css:.1f} px CSS (vista {self.vista} px)', 'calidad')
        cajas = [(e['id'], e['caja']) for e in textos]
        cajas += [('logo', lg['caja'])]
        cajas += [(f"cruz-registro-{i}", Rect(e['cx'] - e['tam'], e['cy'] - e['tam'], 2 * e['tam'], 2 * e['tam']))
                  for i, e in enumerate(x for x in self.el if x['tipo'] == 'cruz' and x.get('registro'))]
        if 'chip' in self.zonas:
            cajas.append(('chip-caja', Rect(**self.zonas['chip'])))
        for e in self.el:
            if e['tipo'] == 'ilustracion':
                cajas.append(('ilustracion', e['caja']))
        choques = []
        for i, (a, ra) in enumerate(cajas):
            for b, rb in cajas[i + 1:]:
                if {a, b} == {'chip', 'chip-caja'}:
                    continue
                if ra.interseca(rb, holgura=1.0):
                    choques.append(f'{a}×{b}')
        regla('sin_choques', not choques, 'ninguno' if not choques else ', '.join(choques), 'calidad')
        return res

    # ---------------------------------------------------------------- SVG
    def svg(self, nombre: str, prefijo_fuentes: str, prefijo_img: str) -> str:
        W, H = self.W, self.H
        f2 = lambda n: f'{n:.2f}'.rstrip('0').rstrip('.')
        partes = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" data-motor="{VERSION_MOTOR}" '
            f'data-pack={quoteattr(str(self.pack.get("id")))} data-modo="{self.modo}">',
            f'  <title>{escape(nombre)} · Umbral BIM · laboratorio motor de piezas</title>',
            f'  <defs><style type="text/css"><![CDATA[{self.ctx.css_fuentes(prefijo_fuentes)}]]></style>',
        ]
        if self.imagen:
            z = self.imagen['zona']
            partes.append(f'    <clipPath id="recorte-imagen"><rect x="{f2(z.x)}" y="{f2(z.y)}" width="{f2(z.w)}" '
                          f'height="{f2(z.h)}" rx="{self.imagen["radio"]}"/></clipPath>')
        partes.append('  </defs>')
        for e in self.el:
            t = e['tipo']
            if t == 'fondo':
                partes.append(f'  <rect id="fondo" x="0" y="0" width="{W}" height="{H}" {self.pintura("fondo")}/>')
            elif t == 'imagen':
                im = self.imagen
                partes.append(f'  <image id="imagen" data-catalogo="{im["id"]}" x="{f2(im["x"])}" y="{f2(im["y"])}" '
                              f'width="{f2(im["w"])}" height="{f2(im["h"])}" preserveAspectRatio="none" '
                              f'clip-path="url(#recorte-imagen)" href="{prefijo_img}{im["ruta"].name}"/>')
                if im['radio']:
                    z = im['zona']
                    partes.append(f'  <rect x="{f2(z.x)}" y="{f2(z.y)}" width="{f2(z.w)}" height="{f2(z.h)}" '
                                  f'rx="{im["radio"]}" fill="none" stroke="{marca.hex_de(self.rgba("filete"))}" '
                                  f'stroke-width="{self.ctx.reglas["filete_px"]}"/>')
            elif t == 'velo':
                vl = next(x for x in self.velos if x.get('id') == e['id'])
                miembros = [x for x in self.velos if not x.get('fijo') and x['grupo'] == vl['grupo']]
                if len(miembros) == 1:
                    r = vl['rect']
                    partes.append(f'  <rect id="{e["id"]}" x="{f2(r.x)}" y="{f2(r.y)}" width="{f2(r.w)}" '
                                  f'height="{f2(r.h)}" fill="{marca.hex_de(vl["color"])}" '
                                  f'fill-opacity="{vl["opacidad"]:.2f}"/>')
                elif vl is miembros[0]:
                    # un grupo se pinta como una sola forma: sin costura ni doble opacidad entre sus partes
                    d = ' '.join(f"M{f2(m['rect'].x)} {f2(m['rect'].y)}h{f2(m['rect'].w)}v{f2(m['rect'].h)}"
                                 f"h{f2(-m['rect'].w)}z" for m in miembros)
                    partes.append(f'  <path id="{vl["grupo"]}" d="{d}" fill="{marca.hex_de(vl["color"])}" '
                                  f'fill-opacity="{vl["opacidad"]:.2f}"/>')
            elif t == 'trama':
                puntos = []
                y = e['y0']
                while y <= e['y1'] + 0.01:
                    x = e['x0']
                    while x <= e['x1'] + 0.01:
                        puntos.append(f'<circle cx="{f2(x)}" cy="{f2(y)}" r="{f2(e["r"])}"/>')
                        x += e['paso']
                    y += e['paso']
                partes.append(f'  <g id="trama" {self.pintura(e["color"])} opacity="{e["opacidad"]}">'
                              + ''.join(puntos) + '</g>')
            elif t == 'cruz':
                c, cx, cy = e['tam'], e['cx'], e['cy']
                partes.append(f'  <g stroke="{marca.hex_de(self.rgba(e["color"]))}" stroke-width="{self.ctx.reglas["filete_px"]}" '
                              f'stroke-linecap="square"><line x1="{f2(cx - c)}" y1="{f2(cy)}" x2="{f2(cx + c)}" y2="{f2(cy)}"/>'
                              f'<line x1="{f2(cx)}" y1="{f2(cy - c)}" x2="{f2(cx)}" y2="{f2(cy + c)}"/></g>')
            elif t == 'linea':
                partes.append(f'  <line id="{e["id"]}" x1="{f2(e["x1"])}" y1="{f2(e["y1"])}" x2="{f2(e["x2"])}" '
                              f'y2="{f2(e["y2"])}" stroke="{marca.hex_de(self.rgba(e["color"]))}" '
                              f'stroke-width="{self.ctx.reglas["filete_px"]}"/>')
            elif t == 'ilustracion':
                partes.append(f'  <g id="ilustracion" data-origen={quoteattr(e["ruta"])} fill="none" '
                              f'transform="translate({f2(e["tx"])},{f2(e["ty"])}) scale({e["k"]:.5f})">'
                              f'{e["interior"]}</g>')
            elif t == 'texto':
                estilo = (f"font-family:'{e['familia']}';font-weight:{e['peso']};font-size:{f2(e['tamano'])}px;"
                          f"letter-spacing:{e['tracking_em']}em;font-feature-settings:{self.rasgos(e['familia'])}")
                r, g, b = self.rgba(e['color'])[:3]
                partes.append(f'  <text id="{e["id"]}" x="{f2(e["x"])}" y="{f2(e["y"])}" text-anchor="{e["anclaje"]}" '
                              f'fill="{marca.hex_de((r, g, b))}" style={quoteattr(estilo)}>{escape(e["texto"])}</text>')
            elif t == 'logo':
                lg = self.logo
                partes.append(f'  <g id="logo" data-origen={quoteattr(str(lg["ruta"]))} '
                              f'transform="translate({f2(lg["x"])},{f2(lg["y"])}) scale({lg["escala"]:.6f})">'
                              f'{lg["interior"]}</g>')
            elif t == 'boton':
                c = e['caja']
                partes.append(f'  <rect id="cta-boton" x="{f2(c.x)}" y="{f2(c.y)}" width="{f2(c.w)}" height="{f2(c.h)}" '
                              f'rx="{e["radio"]}" {self.pintura("cta_boton")}/>')
            elif t == 'chip_fondo':
                c = e['caja']
                partes.append(f'  <rect id="chip-fondo" x="{f2(c.x)}" y="{f2(c.y)}" width="{f2(c.w)}" height="{f2(c.h)}" '
                              f'rx="{e["radio"]}" {self.pintura("chip_fondo")}/>')
        partes.append('</svg>')
        return '\n'.join(partes) + '\n'


# -----------------------------------------------------------------------------
# generar una pieza
# -----------------------------------------------------------------------------

def generar_pieza(ctx: Contexto, nav: Navegador, ruta_pack: Path, dir_salida: Path, codigo: str,
                  ruta_contenido: Path | None = None) -> dict:
    pack = cargar_pack(ruta_pack)
    ruta_contenido = Path(ruta_contenido or LAB / pack['contenido'])
    contenido = cargar_yaml(ruta_contenido)
    comp = Compositor(ctx, nav, pack, contenido)
    comp.componer()
    for sub in ('svg', 'png', 'img', 'fuentes', 'piezas'):
        (dir_salida / sub).mkdir(parents=True, exist_ok=True)
    if not any((dir_salida / 'fuentes').glob('*.woff2')):
        ctx.copiar_fuentes(dir_salida / 'fuentes')
    if comp.imagen:
        destino = dir_salida / 'img' / comp.imagen['ruta'].name
        if not destino.exists():
            shutil.copy2(comp.imagen['ruta'], destino)
    svg = comp.svg(codigo, '../fuentes/', '../img/')
    ruta_svg = dir_salida / 'svg' / f'{codigo}.svg'
    ruta_svg.write_text(svg, encoding='utf-8')
    verificaciones = comp.verificar(svg)
    ruta_png = dir_salida / 'png' / f'{codigo}.png'
    nav.raices['salida'] = dir_salida.resolve()
    estado_fuentes = nav.rasterizar(nav.url('salida', f'svg/{codigo}.svg'), comp.W, comp.H,
                                    ctx.rutas['navegador']['escala_png'], ruta_png)
    cargadas = {f'{fam}|{peso}' for fam, peso, est in estado_fuentes if est == 'loaded'}
    usadas = {f"{e['familia']}|{e['peso']}" for e in comp.el if e['tipo'] == 'texto'}
    faltan = sorted(usadas - cargadas)
    verificaciones.append({'regla': 'fuentes_render', 'ok': not faltan, 'clase': 'ub3',
                           'detalle': f'caras usadas y cargadas al rasterizar: {sorted(usadas)}' if not faltan
                           else f'caras usadas sin cargar al rasterizar: {faltan}'})
    rompe = [x['regla'] for x in verificaciones if x['clase'] == 'ub3' and not x['ok']]
    lg = comp.logo
    info = {
        'codigo': codigo,
        'pack': pack.get('id'),
        'pack_nombre': pack.get('nombre'),
        'pack_archivo': str(Path(ruta_pack).resolve().relative_to(LAB)).replace('\\', '/'),
        'alternativa': pack.get('alternativa'),
        'contenido': str(ruta_contenido.resolve().relative_to(LAB)).replace('\\', '/'),
        'estado': 'exploración' if (rompe or pack.get('exploracion')) else 'cumple UB-3',
        'reglas_rotas': rompe,
        'formato': comp.v['formato'], 'modo': comp.modo, 'ancho': comp.W, 'alto': comp.H,
        'valores': comp.v,
        'derivados': {
            'margen': comp.margen, 'margen_inferior': comp.margen_inf, 'medianil': comp.medianil,
            'modulo': comp.modulo, 'columna': round(comp.col_w, 1), 'fila_grilla': round(comp.fil_h, 1),
            'tamanos_px': comp.t, 'tamanos_css': {k: round(x / comp.px_por_css, 1) for k, x in comp.t.items()},
            'titulo_px': next((e['tamano'] for e in comp.el if e.get('id') == 'titulo-1'), None),
            'zonas': comp.zonas,
            'velos': [{'id': x['id'], 'rect': x['rect'].a_dict(), 'opacidad': x.get('opacidad')}
                      for x in comp.velos if not x.get('fijo')],
            'contrastes': getattr(comp, 'contrastes', {}),
        },
        'notas': comp.notas,
        'verificaciones': verificaciones,
        'logo': {'archivo': Path(lg['ruta']).name, 'variante': lg['variante'], 'composicion': lg['comp'],
                 'ancho_px': round(lg['ancho'], 1), 'sha256': sha16(lg['ruta'])},
        'imagen': ({k: comp.imagen['info'].get(k) for k in
                    ('archivo', 'herramienta', 'modelo', 'prompt', 'parametros', 'job_id', 'referencias_estilo',
                     'semilla', 'proporcion_pedida', 'reproducible', 'sha256')} | {
                       'encaje': comp.v['imagen_encaje']}) if comp.imagen else None,
        'procedencia': {'tokens_css_sha256': sha16(ctx.ruta_tokens), 'motor': VERSION_MOTOR,
                        'generado': datetime.now().isoformat(timespec='seconds')},
        'svg': f'svg/{codigo}.svg', 'png': f'png/{codigo}.png',
    }
    (dir_salida / 'piezas' / f'{codigo}.json').write_text(
        json.dumps(info, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return info


def abrir_navegador(ctx: Contexto) -> Navegador:
    nav = Navegador({'fuentes': ctx.dir_fuentes}, ctx.rutas['navegador']['canal'])
    return nav


def campana(ctx: Contexto, ruta_preset: Path, ruta_contenido: Path, dir_salida: Path) -> list[dict]:
    """Un contenido, todos los formatos de un preset: la campaña sale de una vez."""
    familia = cargar_yaml(ruta_preset)
    infos = []
    with abrir_navegador(ctx) as nav:
        nav.preparar_medicion(ctx.css_fuentes(nav.url('fuentes', '')))
        for formato, ruta_pack in familia['formatos'].items():
            info = generar_pieza(ctx, nav, LAB / ruta_pack, dir_salida, f"{familia['id']}-{formato}", ruta_contenido)
            infos.append(info)
            rotas = '; '.join(info['reglas_rotas']) or '-'
            print(f"{info['codigo']:14s} {info['estado']:12s} {info['ancho']}×{info['alto']}  {rotas}")
    return infos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='orden', required=True)
    p = sub.add_parser('pieza', help='genera una pieza desde un pack')
    p.add_argument('--pack', required=True)
    p.add_argument('--contenido')
    p.add_argument('--salida', default='salida/prueba')
    p.add_argument('--codigo')
    c = sub.add_parser('campana', help='genera todos los formatos de un preset con un mismo contenido')
    c.add_argument('--preset', required=True, help='familia de packs, p. ej. presets/P01.yaml')
    c.add_argument('--contenido', required=True)
    c.add_argument('--salida', default='salida/campana')
    a = ap.parse_args()
    ctx = Contexto()
    if a.orden == 'campana':
        campana(ctx, Path(a.preset), Path(a.contenido), LAB / a.salida)
        return
    with abrir_navegador(ctx) as nav:
        nav.preparar_medicion(ctx.css_fuentes(nav.url('fuentes', '')))
        ruta_pack = Path(a.pack)
        codigo = a.codigo or cargar_pack(ruta_pack).get('id', ruta_pack.stem)
        info = generar_pieza(ctx, nav, ruta_pack, LAB / a.salida, codigo, a.contenido)
    print(json.dumps({k: info[k] for k in ('codigo', 'estado', 'reglas_rotas', 'notas', 'png')},
                     ensure_ascii=False, indent=2))
    for x in info['verificaciones']:
        print(('OK  ' if x['ok'] else 'NO  ') + f"[{x['clase']}] {x['regla']}: {x['detalle']}")


if __name__ == '__main__':
    main()
