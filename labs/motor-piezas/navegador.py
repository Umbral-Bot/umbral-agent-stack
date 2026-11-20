"""Chrome sin ventana para medir texto y pasar SVG a PNG.

Usa el Chrome ya instalado en el equipo a través de Playwright: no descarga
navegadores. Los archivos locales se sirven bajo https://motor.local/<alias>/
porque Chrome bloquea las fuentes @font-face cargadas desde file://.

Medir y rasterizar con el mismo motor de render garantiza que lo que el
motor calcula (anchos, altura de mayúscula) es lo que después se dibuja.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import quote, unquote

from playwright.sync_api import sync_playwright

ORIGEN = 'https://motor.local'
_TIPOS = {
    '.svg': 'image/svg+xml',
    '.woff2': 'font/woff2',
    '.ttf': 'font/ttf',
    '.html': 'text/html; charset=utf-8',
}

_JS_MEDIR = """
async (specs) => {
  const caras = [...new Set(specs.map(s => `${s.peso} 32px "${s.familia}"`))];
  await Promise.all(caras.map(c => document.fonts.load(c)));
  await document.fonts.ready;
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.getElementById('lienzo');
  const cv = document.createElement('canvas').getContext('2d');
  const out = specs.map(s => {
    const t = document.createElementNS(NS, 'text');
    t.setAttribute('x', 0); t.setAttribute('y', 0);
    t.style.fontFamily = `"${s.familia}"`;
    t.style.fontWeight = s.peso;
    t.style.fontSize = s.tamano + 'px';
    t.style.letterSpacing = s.tracking_em + 'em';
    t.style.fontFeatureSettings = s.rasgos;
    t.textContent = s.texto;
    svg.appendChild(t);
    const avance = t.getComputedTextLength();
    svg.removeChild(t);
    cv.font = `${s.peso} ${s.tamano}px "${s.familia}"`;
    const mH = cv.measureText('H');
    const mT = cv.measureText(s.texto || 'H');
    return {avance, cap: mH.actualBoundingBoxAscent,
            asc: mT.actualBoundingBoxAscent, desc: mT.actualBoundingBoxDescent};
  });
  const cargadas = [...document.fonts].filter(f => f.status === 'loaded')
                                      .map(f => `${f.family.replace(/"/g, '')}|${f.weight}`);
  return {medidas: out, cargadas};
}
"""

_JS_LISTO = """
async () => {
  if (document.fonts) { await document.fonts.ready; }
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  return document.fonts ? [...document.fonts].map(f => [f.family.replace(/"/g, ''), f.weight, f.status]) : [];
}
"""


class Navegador:
    """Sesión de Chrome con carpetas locales publicadas bajo alias."""

    def __init__(self, raices: dict, canal: str = 'chrome'):
        self.raices = {alias: Path(r).resolve() for alias, r in raices.items()}
        self.canal = canal
        self._pw = None
        self._nav = None
        self._virtuales: dict[str, tuple[str, str]] = {}
        self._ctx_medida = None
        self._pag_medida = None
        self._cache: dict[tuple, dict] = {}
        self.caras_cargadas: set[str] = set()

    # -- ciclo de vida -------------------------------------------------------
    def __enter__(self):
        self._pw = sync_playwright().start()
        self._nav = self._pw.chromium.launch(channel=self.canal, headless=True)
        return self

    def __exit__(self, *exc):
        if self._ctx_medida:
            self._ctx_medida.close()
        if self._nav:
            self._nav.close()
        if self._pw:
            self._pw.stop()

    # -- servidor local ----------------------------------------------------------
    def url(self, alias: str, ruta: str | Path) -> str:
        return f'{ORIGEN}/{alias}/' + quote(str(ruta).replace('\\', '/'))

    def publicar_texto(self, nombre: str, contenido: str, tipo: str = 'text/html; charset=utf-8') -> str:
        """Publica un documento generado en memoria bajo https://motor.local/_/<nombre>."""
        self._virtuales[nombre] = (contenido, tipo)
        return f'{ORIGEN}/_/{quote(nombre)}'

    def _servir(self, route):
        rel = unquote(route.request.url[len(ORIGEN) + 1:].split('?', 1)[0])
        alias, _, resto = rel.partition('/')
        if alias == '_' and resto in self._virtuales:
            cuerpo, tipo = self._virtuales[resto]
            return route.fulfill(status=200, body=cuerpo, headers={'content-type': tipo})
        raiz = self.raices.get(alias)
        if raiz is None:
            return route.fulfill(status=404, body=f'alias desconocido: {alias}')
        p = (raiz / resto).resolve()
        if raiz not in p.parents or not p.is_file():
            return route.fulfill(status=404, body=f'no encontrado: {rel}')
        tipo = _TIPOS.get(p.suffix.lower()) or mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        return route.fulfill(status=200, body=p.read_bytes(), headers={'content-type': tipo})

    def _pagina(self, ancho: int, alto: int, escala: float):
        ctx = self._nav.new_context(viewport={'width': int(ancho), 'height': int(alto)},
                                    device_scale_factor=escala)
        pag = ctx.new_page()
        pag.route(f'{ORIGEN}/**', self._servir)
        return ctx, pag

    # -- medición de texto -------------------------------------------------------
    def preparar_medicion(self, css_fuentes: str):
        """Abre una página con las @font-face de marca para medir texto."""
        html = ('<!doctype html><html><head><meta charset="utf-8"><style>'
                + css_fuentes + '</style></head><body>'
                '<svg id="lienzo" xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>'
                '</body></html>')
        url = self.publicar_texto('medir.html', html)
        self._ctx_medida, self._pag_medida = self._pagina(800, 600, 1)
        self._pag_medida.goto(url, wait_until='networkidle')

    def medir(self, specs: list[dict]) -> list[dict]:
        """Mide textos. Cada spec: texto, familia, peso, tamano, tracking_em, rasgos.

        Devuelve avance (ancho de avance con tracking, sin el tracking final),
        cap (altura de mayúscula), asc y desc (tinta del texto concreto).
        """
        if self._pag_medida is None:
            raise RuntimeError('llamar a preparar_medicion() antes de medir()')
        claves = [(s['texto'], s['familia'], s['peso'], round(s['tamano'], 3),
                   round(s['tracking_em'], 4), s['rasgos']) for s in specs]
        faltan = [i for i, k in enumerate(claves) if k not in self._cache]
        if faltan:
            res = self._pag_medida.evaluate(_JS_MEDIR, [specs[i] for i in faltan])
            self.caras_cargadas.update(res['cargadas'])
            for i, m in zip(faltan, res['medidas']):
                s = specs[i]
                tracking_px = s['tracking_em'] * s['tamano']
                # Chrome suma el tracking también tras la última letra: se descuenta.
                m['avance'] = m['avance'] - (tracking_px if s['texto'] else 0)
                self._cache[claves[i]] = m
        return [dict(self._cache[k]) for k in claves]

    # -- render ------------------------------------------------------------------
    def rasterizar(self, url_svg: str, ancho: int, alto: int, escala: float, destino: Path) -> list:
        """Carga el SVG como documento y lo captura a `escala` (2 = PNG 2x)."""
        ctx, pag = self._pagina(ancho, alto, escala)
        try:
            pag.goto(url_svg, wait_until='networkidle')
            estado = pag.evaluate(_JS_LISTO)
            Path(destino).parent.mkdir(parents=True, exist_ok=True)
            pag.screenshot(path=str(destino), clip={'x': 0, 'y': 0, 'width': ancho, 'height': alto})
        finally:
            ctx.close()
        return estado

    def evaluar(self, url: str, ancho: int, alto: int, js: str, arg=None):
        """Carga un documento y evalúa JS sobre él (para el análisis de piezas)."""
        ctx, pag = self._pagina(ancho, alto, 1)
        try:
            pag.goto(url, wait_until='networkidle')
            pag.evaluate(_JS_LISTO)
            return pag.evaluate(js, arg) if arg is not None else pag.evaluate(js)
        finally:
            ctx.close()
