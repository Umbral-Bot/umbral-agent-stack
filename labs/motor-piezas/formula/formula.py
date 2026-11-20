"""Camino B del motor de piezas: del contenido de una pieza al prompt de Magnific, sin gastar créditos.

  rutear     elige la ruta (imagen con una categoría, fondo o diagrama) con el léxico de lexico.yaml.
             Si el léxico no decide, deja listo el encargo del clasificador (clasificador.md).
  aceptar    revisa la respuesta del clasificador (paso 6 de ruteo.md) y cierra el ruteo.
  preparar   arma prompt(1): el esqueleto común (prompt1.md) con los datos de la pieza y el bloque
             de su categoría (categorias.yaml).
  validar    revisa el JSON que devuelve prompt(1) (validacion.md). Si pasa, arma el texto que va a
             cada motor (Magnific One con kit o Nano Banana 2.1 sin kit) con el hash del cuerpo.
  regresion  corre los casos de fixtures.yaml y compara la ruta con la esperada.

Nada de esto llama a Magnific ni gasta créditos: el pedido lo aprueba David.

Uso (desde labs/motor-piezas):
  python formula/formula.py rutear --contenido contenido/articulo-ejemplo.yaml --salida formula/demo/ruteo.json
  python formula/formula.py preparar --ruteo formula/demo/ruteo.json --salida formula/demo/prompt1.md
  python formula/formula.py validar --ruteo formula/demo/ruteo.json --prompt2 formula/demo/prompt2.json \\
      --salida formula/demo/pedido.json
  python formula/formula.py regresion
"""
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import yaml

AQUI = Path(__file__).resolve().parent
LAB = AQUI.parent
LEX = yaml.safe_load((AQUI / 'lexico.yaml').read_text(encoding='utf-8'))
CATS = {c['id']: c for c in yaml.safe_load((AQUI / 'categorias.yaml').read_text(encoding='utf-8'))['categorias']}
DESEMPATE = ['comparacion', 'hallazgo', 'interfaz', 'pendiente', 'transformacion', 'evento']
REGISTRO = AQUI / 'registro.jsonl'

# Paso 12 de ruteo.md: lo que el código añade a cada motor. El modelo de lenguaje no escribe la marca.
COLA_MG1 = ' No text, no markers, no logo.'
BLOQUE_MARCA = {
    '16:9': 'in a 16:9 frame, the subject about 45 percent of the width and half the height',
    '21:9': 'in a wide 21:9 frame, the subject about 75 percent of the width with clear margins at both ends',
}
BLOQUE_MARCA = {k: ('Drawn as a flat vector isometric technical line illustration ' + v + '. Thin uniform #074E43 and '
                    '#1F2328 lines, plain white #FFFFFF faces; the teal parts are filled flat #0FA994 and are the only '
                    'colour. Solid #FAFAF9 off-white background with faint pale construction grid lines to the edges. '
                    'Strict isometric projection, no vanishing point. Even flat daylight: no shadows, glow, gradients '
                    'or highlights. Contains no text, letters, numbers, labels, markers, symbols, logo or watermark.')
                for k, v in BLOQUE_MARCA.items()}
MOTORES = {
    'mg1_kit': {'modelo': 'magnific-one', 'kit': 'hu2CvqLJlt (Umbral BIM)', 'referencia_estilo': 'lJo6GJSgv9',
                'resolucion': '2k', 'creditos': 180},
    'nb21_sin_kit': {'modelo': 'nano-banana-2.1', 'kit': None, 'referencia_estilo': 'lJo6GJSgv9',
                     'resolucion': '2k', 'creditos': 65},
}


# ---------------------------------------------------------------------------------------------- texto
def normalizar(s: str) -> str:
    """Minúsculas y sin tildes, carácter por carácter: el resultado mide lo mismo que el original,
    así una coincidencia en el texto normalizado se puede citar en el original."""
    out = []
    for ch in unicodedata.normalize('NFC', s or ''):
        base = ''.join(c for c in unicodedata.normalize('NFD', ch) if not unicodedata.combining(c)).lower()
        out.append(base if len(base) == 1 else ch)
    return ''.join(out)


def leer_contenido(fuente) -> dict:
    """El contenido del motor (contenido/*.yaml) o un caso de fixtures.yaml, a los campos del ruteo."""
    if isinstance(fuente, (str, Path)):
        ruta = Path(fuente)
        c = yaml.safe_load((ruta if ruta.is_absolute() else LAB / ruta).read_text(encoding='utf-8'))
        origen = str(fuente)
    else:
        c, origen = dict(fuente), 'inline'
    if c.get('fixture_repo'):         # un visual brief v2 del repo: central_fact y ignored_consequence
        v2 = yaml.safe_load((LAB.parent.parent / c['fixture_repo']).read_text(encoding='utf-8'))
        c.setdefault('titulo', v2['central_fact'])
        c.setdefault('bajada', v2['ignored_consequence'])
        origen = c['fixture_repo']
    titulo = c.get('titulo') or c.get('titular') or ''
    titular = ' '.join(titulo) if isinstance(titulo, list) else str(titulo)
    # En el Preset 02 el campo `cuerpo` es la bajada; en los eventos, el subtítulo hace de bajada.
    bajada = c.get('bajada') or c.get('cuerpo') or c.get('subtitulo') or ''
    return {
        'id': c.get('id', origen), 'origen': origen,
        'kicker': str(c.get('kicker', '')).strip(), 'titular': unicodedata.normalize('NFC', titular.strip()),
        'bajada': unicodedata.normalize('NFC', str(bajada).strip()),
        'extracto': str(c.get('extracto') or c.get('texto') or '')[:600],
        'filas': [str(f.get('etiqueta', '')) for f in c.get('filas') or []],
        'cta': str(c.get('cta', '')), 'tipo_recurso': str(c.get('tipo_recurso') or c.get('kicker', '')),
        'override': c.get('grafico') or {},
    }


def palabras_idx(texto: str):
    return [(m.start(), m.end()) for m in re.finditer(r'\w+', texto)]


def idx_de(toks, pos: int) -> int:
    for i, (a, b) in enumerate(toks):
        if b > pos:
            return i
    return len(toks)


def solapa(span, usados) -> bool:
    return any(span[0] < b and a < span[1] for a, b in usados)


def buscar_cerca(c: dict, texto: str, usados, ambos: bool):
    """Primer par a `max` palabras o menos (en cualquier orden y sin cruzar de titular a bajada)."""
    toks = palabras_idx(texto)
    for ma in re.finditer(c['a'], texto):
        if solapa(ma.span(), usados):
            continue
        ia0, ia1 = idx_de(toks, ma.start()), idx_de(toks, ma.end() - 1)
        for mb in re.finditer(c['b'], texto):
            if mb.start() < ma.end() and ma.start() < mb.end():
                continue
            ib0, ib1 = idx_de(toks, mb.start()), idx_de(toks, mb.end() - 1)
            entre = ib0 - ia1 - 1 if mb.start() >= ma.end() else ia0 - ib1 - 1
            lo, hi = min(ma.start(), mb.start()), max(ma.end(), mb.end())
            if 0 <= entre <= c['max'] and '\n' not in texto[lo:hi]:
                return ((lo, hi) if ambos else ma.span()), (lo, hi)
    return None


# ---------------------------------------------------------------------------------------------- ruteo
def complementos(texto: str):
    """«acordar», «definir», «consensuar»: el primer complemento decide si suma a interfaz o a pendiente."""
    cfg, toks, hallados = LEX['complemento'], palabras_idx(texto), []
    for m in re.finditer(cfg['verbo'], texto):
        i = idx_de(toks, m.end() - 1)
        for a, b in toks[i + 1:i + 1 + cfg['max']]:
            if '\n' in texto[m.end():a]:
                break
            palabra = texto[a:b]
            destino = next((cat for cat, p in cfg['destinos'].items() if re.match(p, palabra)), None)
            if destino:
                hallados.append((destino, (m.start(), b)))
                break
    return hallados


def puntuar(texto: str, kicker_n: str, factor: float = 1.0):
    """Puntaje por categoría sobre un texto normalizado. Devuelve {cat: {total, senales, directo, anti}}."""
    compl = complementos(texto)
    res = {}
    for cat, senales in LEX['categorias'].items():
        usados, total, hallazgos, directo, anti = [], 0.0, [], False, False
        positivas = sorted([s for s in senales if s['peso'] > 0], key=lambda s: -s['peso'])
        fuertes = [s for s in positivas if s['peso'] >= 3]
        resto = [s for s in positivas if s['peso'] < 3]
        extra = [{'peso': LEX['complemento']['peso'], 'complemento': span} for d, span in compl if d == cat][:1]
        for s in fuertes + extra + resto:
            encontrado = None
            if 'complemento' in s:
                if not solapa(s['complemento'], usados):
                    encontrado = (s['complemento'], s['complemento'])
            elif 'kicker' in s:
                if re.search(s['kicker'], kicker_n) and (not s.get('requiere_objeto')
                                                          or re.search(LEX['objetos_aec'], texto)):
                    hallazgos.append({'peso': s['peso'] * factor, 'cita': 'kicker', 'span': None})
                    total += s['peso'] * factor
                continue
            elif 'patron' in s:
                encontrado = next(((m.span(), m.span()) for m in re.finditer(s['patron'], texto)
                                   if not solapa(m.span(), usados)), None)
            else:
                encontrado = buscar_cerca(s['cerca'], texto, usados, s.get('consume') == 'ambos')
            if encontrado:
                consumo, cita = encontrado
                usados.append(consumo)
                total += s['peso'] * factor
                hallazgos.append({'peso': s['peso'] * factor, 'span': cita})
                directo = directo or bool(s.get('gana_directo'))
        for s in senales:
            if s['peso'] < 0 and 'patron' in s:
                m = re.search(s['patron'], texto)
                if m:
                    total += s['peso'] * factor
                    hallazgos.append({'peso': s['peso'] * factor, 'span': m.span()})
                    anti = True
        res[cat] = {'total': total, 'senales': hallazgos, 'directo': directo, 'anti': anti}
    return res


def gate_adr006(texto_n: str):
    """Paso 3: una cifra o pasos enumerados en el titular o la bajada. Devuelve (tipo, span) o None."""
    g = LEX['gate']
    t = re.sub(g['excluir'], lambda m: ' ' * len(m.group(0)), texto_n)   # normas, versiones y años sueltos
    for tipo, patron in [('cifra', r'\b' + g['numero'] + r'\s*' + g['unidad']), ('cifra', g['verbo_cifra']),
                         ('cifra', g['de_cada']), ('pasos', g['pasos']), ('pasos', g['enumeracion']),
                         ('pasos', g['secuencia'])]:
        m = re.search(patron, t)
        if m:
            return tipo, m.span()
    for linea in t.split('\n'):
        if len(re.findall(g['separadores'], linea)) >= 2:
            ini = texto_n.find(linea)
            return 'pasos', (ini, ini + len(linea))
    return None


def rutear_pieza(p: dict) -> dict:
    r = {'id': p['id'], 'contenido': p['origen'], 'lexico': LEX['version'], 'kicker': p['kicker'],
         'titular': p['titular'], 'bajada': p['bajada'], 'override': p['override'] or None}
    if not (p['kicker'] and p['titular'] and p['bajada']):
        return {**r, 'ruta': 'detenida', 'motivo': 'falta kicker, titular o bajada'}
    original = p['titular'] + '\n' + p['bajada']
    texto = normalizar(p['titular']) + '\n' + normalizar(p['bajada'])
    kn = normalizar(p['kicker']).strip()
    ov = p['override'] or {}
    cita = lambda span: original[span[0]:span[1]].replace('\n', ' / ')

    # Paso 0: la instrucción de David manda sobre los pasos 1 a 6 (nunca sobre la validación).
    if ov.get('ruta') in ('fondo', 'diagrama'):
        return {**r, 'ruta': ov['ruta'], 'metodo': 'override', 'motivo': 'instrucción de David'}

    # Paso 1: evento por código.
    ev = LEX['evento']
    por_kicker = re.search(ev['kicker'], kn)
    por_filas = [f for f in p['filas'] if normalizar(f).strip() in ev['filas']]
    por_cta = re.search(ev['cta'], normalizar(p['cta']).strip())
    if (por_kicker or por_filas or por_cta) and not ov.get('categoria'):
        motivo = ('kicker «%s»' % p['kicker']) if por_kicker else ('filas %s' % ', '.join(por_filas)) if por_filas \
            else 'CTA «%s»' % p['cta']
        return {**r, 'ruta': 'imagen', 'categoria': 'evento', 'metodo': 'regla', 'motivo': motivo,
                'evidencia': [p['titular']]}

    pide_imagen = ov.get('ruta') == 'imagen'
    if not pide_imagen:
        # Paso 2: fondo institucional (antes del gate, para que un aniversario no termine en diagrama).
        if re.search(LEX['institucional']['kicker'], kn) and not re.search(LEX['objetos_aec'], kn + '\n' + texto):
            return {**r, 'ruta': 'fondo', 'metodo': 'salida', 'motivo': 'institucional',
                    'imagen': {'tipo': 'fondo', 'imagen_recorte_fondo': 'optimo'}}
        # Paso 3: gate ADR-006.
        g = gate_adr006(texto)
        if g:
            return {**r, 'ruta': 'diagrama', 'metodo': 'salida', 'motivo': 'gate ADR-006: ' + g[0],
                    'cita': cita(g[1]), 'capa3_pendiente': True,
                    'nota': 'mientras no exista la capa 3, la máscara lleva el fondo del camino A y la cifra '
                            'queda en el copy',
                    'imagen': {'tipo': 'fondo', 'imagen_recorte_fondo': 'optimo'}}
    else:
        # Con instrucción de imagen, la cifra o los pasos salen del texto y se re-rutea desde el paso 4.
        quitadas = []
        g = gate_adr006(texto)
        while g:
            quitadas.append(cita(g[1]))
            texto = texto[:g[1][0]] + ' ' * (g[1][1] - g[1][0]) + texto[g[1][1]:]
            g = gate_adr006(texto)
        if quitadas:
            r['fuera_del_prompt'] = quitadas

    # Paso 4: puntaje léxico.
    pt = puntuar(texto, kn)
    pc = puntuar(normalizar(p['extracto']), kn, 0.5) if p['extracto'] else {c: {'total': 0} for c in pt}
    r['puntajes'] = {c: v['total'] for c, v in pt.items() if v['total']}
    r['senales'] = [{'categoria': c, 'peso': s['peso'], 'cita': 'kicker' if s['span'] is None else cita(s['span'])}
                    for c, v in pt.items() for s in v['senales']]
    orden = sorted(pt, key=lambda c: (-pt[c]['total'], -pc[c]['total'], DESEMPATE.index(c)))
    evidencia = lambda c: [cita(s['span']) for s in pt[c]['senales'] if s['span'] and s['peso'] > 0][:2]

    if ov.get('categoria'):
        return {**r, 'ruta': 'imagen', 'categoria': ov['categoria'], 'metodo': 'override',
                'motivo': 'instrucción de David', 'evidencia': evidencia(ov['categoria'])}
    comp = pt['comparacion']
    if comp['directo'] and not comp['anti']:
        return {**r, 'ruta': 'imagen', 'categoria': 'comparacion', 'metodo': 'regla',
                'motivo': 'comparación con señal fuerte (CAND-WLCA-01)', 'evidencia': evidencia('comparacion')}
    a, b = orden[0], orden[1]
    if pt[a]['total'] >= 3 and pt[a]['total'] - pt[b]['total'] >= 2:
        return {**r, 'ruta': 'imagen', 'categoria': a, 'metodo': 'regla',
                'motivo': f"{a} {pt[a]['total']:g} contra {b} {pt[b]['total']:g}", 'evidencia': evidencia(a)}

    # Paso 5: el léxico no decide; queda el encargo del clasificador.
    if pt[a]['total'] >= 1:
        candidatas = [a] + ([b] if pt[b]['total'] > 0 else [])
        motivo = f"{a} {pt[a]['total']:g} y {b} {pt[b]['total']:g}: sin ventaja de 2"
    else:
        candidatas = [c for c in DESEMPATE if c != 'evento' or pt['evento']['total'] > 0]
        motivo = 'ninguna categoría suma (las señales se anulan o no hay)'
    return {**r, 'ruta': 'clasificar', 'metodo': 'llm', 'motivo': motivo, 'candidatas': candidatas + ['fondo'],
            'prompt_clasificador': prompt_clasificador(p, candidatas)}


def prompt_clasificador(p: dict, candidatas) -> str:
    t = (AQUI / 'clasificador.md').read_text(encoding='utf-8')
    t = re.sub(r'<!--.*?-->\n?', '', t, flags=re.S)
    lineas = '\n'.join(f"- {c}: {' '.join(CATS[c]['cuando'].split())}" for c in candidatas)
    lineas += '\n- fondo: ninguna categoría cuenta lo que dice el copy; la pieza lleva el fondo abstracto.'
    for k, v in {'kicker': p['kicker'], 'titular': p['titular'], 'bajada': p['bajada'],
                 'categorias_permitidas': lineas}.items():
        t = t.replace('{' + k + '}', v)
    return t


SUJETO_PROHIBIDO = re.compile(
    r'\b(personas?|gente|equipos?|ingenier[oa]s?|trabajador(es)?|manos?|pantallas?|monitor(es)?|computador(es)?|'
    r'documentos?|hojas?|carpetas?|archivos?|robots?|cerebros?|chips?|person|people|workers?|engineers?|hands?|'
    r'teams?|screens?|laptops?|tablets?|documents?|papers?|sheets?|folders?|files?|brains?)\b', re.I)


def aceptar_clasificacion(r: dict, clas: dict) -> dict:
    """Paso 6 de ruteo.md."""
    base = {k: v for k, v in r.items() if k != 'prompt_clasificador'}
    base['clasificador'] = clas
    cat, conf = clas.get('categoria'), float(clas.get('confianza') or 0)
    fondo = lambda motivo, **extra: {**base, 'ruta': 'fondo', 'metodo': 'llm', 'motivo': motivo, 'confianza': conf,
                                     'imagen': {'tipo': 'fondo', 'imagen_recorte_fondo': 'optimo'}, **extra}
    if cat == 'fondo':
        return fondo('el clasificador eligió fondo')
    if cat not in r.get('candidatas', []):
        return fondo(f'categoría «{cat}» fuera de las permitidas')
    evid = clas.get('evidencia') or []
    if not evid or any(e not in r['titular'] and e not in r['bajada'] for e in evid):
        return fondo('evidencia que no es cita literal del titular o la bajada')
    suj = clas.get('sujeto_candidato') or ''
    if not suj or re.search(r'\b[A-Z]{2,}\b', suj) or SUJETO_PROHIBIDO.search(suj):
        return fondo(f'sujeto candidato que no es un objeto: «{suj}»')
    if conf < 0.5:
        return fondo('confianza menor a 0,50')
    if conf < 0.7:
        return fondo('confianza entre 0,50 y 0,69', hitl=f'candidata a B: {cat}')
    out = {**base, 'ruta': 'imagen', 'categoria': cat, 'metodo': 'llm', 'confianza': conf,
           'motivo': f'clasificador, confianza {conf:.2f}', 'evidencia': evid,
           'alternativa': clas.get('alternativa'), 'compara_clasificador': clas.get('compara')}
    if not r.get('puntajes', {}).get(cat):
        out['hitl'] = 'ruteo_dudoso: el copy no trae ninguna señal léxica de esa categoría'
    return out


# ---------------------------------------------------------------------------------------------- prompt(1)
SLOTS = ['tipo_recurso', 'kicker', 'titular', 'bajada', 'cuerpo', 'categoria_id', 'categoria_nombre', 'metodo_ruta',
         'evidencia_ruteo', 'override', 'motor', 'sujetos_recientes', 'categoria_bloque']


def sujetos_recientes(n: int = 5):
    if not REGISTRO.exists():
        return []
    filas = [json.loads(x) for x in REGISTRO.read_text(encoding='utf-8').splitlines() if x.strip()]
    return [f['sujeto'] for f in filas if f.get('sujeto')][-n:]


def armar_prompt1(r: dict, p: dict, motor: str, recientes, errores=None) -> str:
    if r.get('ruta') != 'imagen':
        raise SystemExit(f"la pieza no va a imagen (ruta {r.get('ruta')}): no hay prompt(1) que armar")
    cat = CATS[r['categoria']]
    ov = r.get('override') or {}
    texto_ov = 'ninguna'
    if ov:
        texto_ov = ', '.join(f'{k}: {v}' for k, v in ov.items())
    if r.get('fuera_del_prompt'):
        texto_ov += '; pide imagen: deja fuera del prompt «' + '», «'.join(r['fuera_del_prompt']) + '»'
    valores = {
        'tipo_recurso': p['tipo_recurso'], 'kicker': p['kicker'], 'titular': p['titular'], 'bajada': p['bajada'],
        'cuerpo': p['extracto'] or '—', 'categoria_id': cat['id'], 'categoria_nombre': cat['nombre'],
        'metodo_ruta': r['metodo'], 'evidencia_ruteo': ' · '.join(r.get('evidencia') or []) or '—',
        'override': texto_ov, 'motor': motor, 'sujetos_recientes': ', '.join(recientes) or 'ninguno',
        'categoria_bloque': cat['bloque_prompt1'].strip(),
    }
    t = (AQUI / 'prompt1.md').read_text(encoding='utf-8')
    t = re.sub(r'<!--.*?-->\n?', '', t, flags=re.S)
    for k in SLOTS:
        t = t.replace('{' + k + '}', str(valores[k]))
    if errores:
        t += ('\n## Reintento\nTu respuesta anterior no pasó la validación. Corrige estos puntos y responde de nuevo '
              'el JSON completo:\n' + '\n'.join(f'- {e}' for e in errores) + '\n')
    return t.strip() + '\n'


# ---------------------------------------------------------------------------------------------- validación
COLORES = r'\b(red|orange|yellow|green|blue|cyan|turquoise|purple|pink|black|white|grey|gray|brown|gold|silver|dark)\b'
ESTILO = r'\b(flat vector|minimal|clean|elegant|sleek|modern|futuristic|cinematic|photorealistic|vibrant)\b'
NUM_EN = r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|hundred|thousand|half|double)\s+' \
         r'(weeks?|days?|months?|years?|hours?|times|percent|per cent)\b|\b(twice|percent|per cent)\b'
MARCAS = ['BIM', 'IFC', 'IDS', 'BCF', 'RFI', 'CDE', 'ISO', 'AI', 'IA', 'Revit', 'Navisworks', 'Solibri', 'Autodesk',
          'Dynamo', 'Rhino', 'Tekla', 'Speckle', 'Procore', 'Magnific', 'Umbral']
NEGACION = r"\b(no|not|never|without|neither|nor|none|nothing|nobody)\b|n't\b"
LISTA_NEGRA = ['text', 'letter', 'word', 'label', 'caption', 'sign', 'signage', 'logo', 'screen', 'monitor', 'laptop',
               'tablet', 'dashboard', 'interface', 'app', 'chart', 'graph', 'diagram', 'infographic', 'arrow', 'icon',
               'symbol', 'marker', 'pin', 'document', 'paper', 'sheet', 'folder', 'file', 'stamp', 'calendar', 'clock',
               'person', 'people', 'worker', 'engineer', 'hand', 'team', 'avatar', 'silhouette', 'robot', 'brain',
               'chip', 'circuit', 'hologram', 'drone', 'scan', 'magnifying', 'glow', 'neon', 'gradient', 'shadow',
               'reflection', 'photo', 'realistic', 'render', '3D', 'blur', 'bokeh', 'cutaway', 'cross-section',
               'sectional', 'exploded', 'x-ray', 'dashed', 'dotted', 'faint', 'ghost', 'transparent', 'translucent',
               'question mark', 'check mark', 'tick', 'warning', 'glass box', 'showcase', 'before and after']
NO_21X9 = ['row of', 'rows', 'each', 'every bay', 'series', 'sequence', 'repeated', 'timeline', 'stages', 'steps',
           'one after another']
POR_CATEGORIA = {   # (debe contener, en cada cuerpo; prohibidas)
    'hallazgo': (None, ['fixed', 'resolved', 'repaired', 'rerouted', 'solved', 'corrected', 'alternative', 'bypass']),
    'comparacion': ([r'\bhalf\b|\bhalves\b', r'\bseam\b'],
                    ['better', 'best', 'winner', 'preferred', 'chosen', 'selected', 'favoured', 'old', 'new', 'worn',
                     'damaged', 'cracked', 'broken', 'before', 'after', 'balance', 'versus']),
    'interfaz': ([r'\bplate\b|\bjoint\b|\bmeets?\b|\bflush\b|\boffset\b'],
                 ['cable', 'wire', 'plug', 'socket', 'cloud', 'network', 'data', 'stream', 'puzzle', 'connector']),
    'pendiente': (None, ['filled', 'delivered', 'arrives', 'installed', 'received', 'answered', 'question',
                         'decision', 'owner', 'chair']),
    'transformacion': ([r'\bfootprint\b|\boutline\b', r'\b(rises|grows|turns)\b'],
                       ['floor plan', 'plan view', 'blueprint', 'drawing', 'sketch', 'dimension', 'phase', 'crane',
                        'worker']),
    'evento': ([r'Every other part is plain line work\.$'],
               ['session', 'webinar', 'workshop', 'audience', 'stage', 'podium', 'microphone', 'speaker',
                'leader line', 'part number', 'light bulb']),
}
VACIAS = {'a', 'an', 'the', 'of', 'and', 'or', 'to', 'in', 'on', 'at', 'with', 'its', 'it', 'one', 'that', 'this',
          'from', 'for', 'by', 'as', 'is', 'are', 'be', 'into', 'out', 'over', 'under', 'part', 'parts'}


def palabra(w: str) -> str:
    """Patrón de palabra completa, sin distinguir mayúsculas, con plural simple."""
    return r'(?<![\w-])' + re.escape(w) + r'(s|es)?(?![\w-])'


def nucleo(sujeto: str) -> str:
    """Sustantivo núcleo del sujeto (aproximado): la última palabra antes de «with», «where», «of», una coma…"""
    s = re.split(r'\b(with|where|carrying|of|that|which|rising|running|under|over|on|in|between)\b|,',
                 sujeto.lower())[0]
    ws = [w for w in re.findall(r'[a-z][a-z-]*', s) if w not in VACIAS | {'compact', 'long', 'low', 'wide', 'single'}]
    return re.sub(r's$', '', ws[-1]) if ws else ''


def sujeto_del_ejemplo(cat: dict) -> str:
    m = re.match(r'Isometric line illustration of (.+?), whole and centred', cat['ejemplo_prompt2_16_9'])
    return m.group(1) if m else ''


def validar_prompt2(r: dict, j: dict, recientes) -> tuple[list, list]:
    """Las comprobaciones 1 a 13 de validacion.md. Devuelve (errores, avisos)."""
    E, A = [], []
    # 1 · Forma
    if j.get('estado') not in ('OK', 'NO_ENCAJA', 'CIFRA'):
        return [f"1 · estado «{j.get('estado')}» no es OK, NO_ENCAJA ni CIFRA"], A
    if j['estado'] != 'OK':
        return E, A
    if j.get('categoria') != r['categoria']:
        E.append(f"1 · la categoría «{j.get('categoria')}» no es la ruteada «{r['categoria']}»")
    for campo in ['compara', 'evidencia', 'acentos', 'motivo', 'relacion', 'no_mostrar', 'prompt_16x9',
                  'prompt_21x9']:
        v = j.get(campo)
        if not v or (isinstance(v, list) and not all(v)):
            E.append(f'1 · el campo «{campo}» está vacío')
    suj = j.get('sujeto') or {}
    if not suj.get('compacto') or not suj.get('alargado'):
        E.append('1 · falta el sujeto compacto o el alargado')
    if E:
        return E, A
    p16, p21, acentos = j['prompt_16x9'].strip(), j['prompt_21x9'].strip(), j['acentos']
    cuerpos = {'16:9': p16, '21:9': p21}
    # 2 · Largo
    for f, c in cuerpos.items():
        n = len(c.split())
        if not 25 <= n <= 55:
            E.append(f'2 · {f}: {n} palabras (van de 25 a 55)')
        if len(c) > 400:
            E.append(f'2 · {f}: {len(c)} caracteres (máximo 400)')
    if p16 == p21:
        E.append('2 · los cuerpos 16:9 y 21:9 son iguales')
    # 3 · Marco literal
    if not p16.startswith('Isometric line illustration of '):
        E.append('3 · 16:9 no empieza con «Isometric line illustration of »')
    for fijo in [', whole and centred with wide empty space around it. ', 'flat teal, the ']:
        if fijo not in p16:
            E.append(f'3 · 16:9 no contiene «{fijo.strip()}»')
    if not p21.startswith('Isometric line illustration: '):
        E.append('3 · 21:9 no empieza con «Isometric line illustration: »')
    for fijo in [', centred, empty margins at both ends', 'flat teal, the single ']:
        if fijo not in p21:
            E.append(f'3 · 21:9 no contiene «{fijo.strip()}»')
    # 4 · Acentos
    n_ac = len(acentos)
    esperado = {'evento': 1, 'comparacion': 2}.get(r['categoria'])
    if not 1 <= n_ac <= 2 or (esperado and n_ac != esperado):
        E.append(f"4 · {n_ac} acentos (en {r['categoria']} van {esperado or '1 o 2'})")
    solo = 'Only one part is flat teal' if n_ac == 1 else 'Only two parts are flat teal'
    for f, c in cuerpos.items():
        if solo not in c:
            E.append(f'4 · {f} no dice «{solo}», que es lo que corresponde a {n_ac} acento(s)')
        if len(re.findall(r'\bteal\b', c, re.I)) != 1:
            E.append(f'4 · {f}: «teal» tiene que aparecer una sola vez')
        for ac in acentos:
            if ac not in c:
                E.append(f'4 · {f}: el acento «{ac}» no aparece literal')
    for ac in acentos:
        if not 2 <= len(ac.split()) <= 6:
            E.append(f'4 · el acento «{ac}» tiene {len(ac.split())} palabras (van de 2 a 6)')
    for f, c in cuerpos.items():
        # 5 · Color y estilo
        for patron, que in [(r'#[0-9a-fA-F]{3,6}\b', 'un código de color'), (COLORES, 'un color'),
                            (ESTILO, 'un adjetivo de estilo')]:
            m = re.search(patron, c, re.I)
            if m:
                E.append(f'5 · {f}: {que} («{m.group(0)}»)')
        # 6 · Cifras
        m = re.search(r'[0-9]', c) or re.search(NUM_EN, c, re.I)
        if m:
            E.append(f'6 · {f}: una cifra («{m.group(0)}»)')
        # 7 · Siglas y marcas
        m = re.search(r'\b[A-Z]{2,}\b', c)
        if m:
            E.append(f'7 · {f}: una sigla («{m.group(0)}»)')
        for marca in MARCAS:
            if re.search(r'\b' + re.escape(marca) + r'\b', c, re.I):
                E.append(f'7 · {f}: una marca o sigla («{marca}»)')
        # 8 · Negaciones
        m = re.search(NEGACION, c, re.I)
        if m:
            E.append(f'8 · {f}: una negación («{m.group(0)}»)')
        # 9 · Lista negra
        for w in LISTA_NEGRA:
            m = re.search(palabra(w), c, re.I)
            if m:
                E.append(f'9 · {f}: palabra de la lista negra («{m.group(0)}»)')
        # 11 · Reglas de la categoría
        debe, prohibidas = POR_CATEGORIA[r['categoria']]
        for patron in debe or []:
            if not re.search(patron, c, re.I if not patron.endswith(r'\.$') else 0):
                E.append(f"11 · {f}: en {r['categoria']} tiene que aparecer {patron}")
        for w in prohibidas:
            m = re.search(palabra(w), c, re.I)
            if m:
                E.append(f"11 · {f}: «{m.group(0)}» no va en {r['categoria']}")
    if r['categoria'] == 'pendiente':
        if not any(re.search(r'\bempty\b', a, re.I) for a in acentos):
            E.append('11 · pendiente: un acento tiene que contener «empty»')
        if not re.search(r'\b(stops|short|gap|ends)\b', j['relacion'], re.I):
            E.append('11 · pendiente: la relación tiene que decir stops, short, gap o ends')
    # 10 · Regla del 21:9
    if 'the single' not in p21:
        E.append('10 · 21:9 no contiene «the single»')
    for w in NO_21X9:
        if re.search(r'\b' + re.escape(w) + r'\b', p21, re.I):
            E.append(f'10 · 21:9: «{w}» lo convierte en fila o serie')
    # 12 · Sujeto no repetido
    nu = nucleo(suj['compacto'])
    ejemplo = nucleo(sujeto_del_ejemplo(CATS[r['categoria']]))
    previos = {nucleo(s): s for s in recientes}
    if nu and nu == ejemplo:
        E.append(f'12 · el sujeto («{nu}») es el del ejemplo de la categoría')
    if nu in previos:
        E.append(f'12 · el sujeto («{nu}») repite el de una pieza reciente («{previos[nu]}»): monotonía')
    # 13 · Revisión semántica (el código solo comprueba que exista; la alineación la juzga otro)
    texto_cuerpos = (p16 + ' ' + p21).lower()
    propios = set(re.findall(r'[a-z]+', (suj['compacto'] + ' ' + suj['alargado'] + ' ' + ' '.join(acentos) + ' '
                                         + j['motivo']).lower()))
    for par in j['no_mostrar']:
        en = (par.get('en') or '').lower().strip() if isinstance(par, dict) else ''
        if not en:
            E.append('13 · un elemento de no_mostrar no trae su versión en inglés')
            continue
        if re.search(r'\b' + re.escape(en) + r'\b', texto_cuerpos):
            E.append(f'13 · lo que no se muestra aparece en el prompt («{en}»)')
            continue
        for w in set(re.findall(r'[a-z]{4,}', en)) - VACIAS - propios:
            if re.search(palabra(w), texto_cuerpos):
                A.append(f'13 · «{w}» (de no_mostrar «{en}») aparece en el prompt: revisar')
    for e in j['evidencia']:
        if e not in r['titular'] and e not in r['bajada']:
            E.append(f'13 · la evidencia «{e}» no es cita literal del titular o la bajada')
    # Avisos que no bloquean
    if not 2 <= len(j['motivo'].split()) <= 8:
        A.append(f"motivo de {len(j['motivo'].split())} palabras (van de 2 a 8)")
    if re.match(r'(the|a|an)\b', j['motivo'], re.I):
        A.append('el motivo empieza con artículo')
    return E, A


def ensamblar(j: dict) -> tuple[list, list]:
    """14 · El texto de cada motor. Devuelve (pedidos, errores)."""
    pedidos, E = [], []
    for fmt, clave, imagen in [('16:9', 'prompt_16x9', 'principal'), ('21:9', 'prompt_21x9', 'ancha')]:
        cuerpo = j[clave].strip()
        h = hashlib.sha256(cuerpo.encode('utf-8')).hexdigest()[:16]
        for motor, cfg in MOTORES.items():
            texto = cuerpo + COLA_MG1 if motor == 'mg1_kit' else cuerpo + ' ' + BLOQUE_MARCA[fmt]
            if motor == 'mg1_kit' and not texto.endswith('No text, no markers, no logo.'):
                E.append(f'14 · {fmt} mg1: no termina en la cola')
            if motor == 'nb21_sin_kit':
                if texto.count(BLOQUE_MARCA[fmt]) != 1:
                    E.append(f'14 · {fmt} nb21: el bloque de marca no aparece una sola vez')
                if re.search(r'#[0-9a-fA-F]{3,6}\b', texto.replace(BLOQUE_MARCA[fmt], '')):
                    E.append(f'14 · {fmt} nb21: hay un código de color fuera del bloque de marca')
            if not texto.startswith(cuerpo):
                E.append(f'14 · {fmt} {motor}: el cuerpo cambió al ensamblar')
            pedidos.append({'imagen': imagen, 'proporcion': fmt, 'motor': motor, **cfg, 'hash_cuerpo': h,
                            'prompt_enviado': texto})
    return pedidos, E


# ---------------------------------------------------------------------------------------------- órdenes
def leer_json(ruta) -> dict:
    return json.loads(Path(ruta).read_text(encoding='utf-8'))


def escribir(ruta, datos, texto=False):
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(datos if texto else json.dumps(datos, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'→ {destino}')


def contenido_de(r: dict) -> dict:
    return leer_contenido(r['contenido'])


def o_rutear(a):
    r = rutear_pieza(leer_contenido(a.contenido))
    resumen = f"{r['id']}: ruta {r['ruta']}"
    if r.get('categoria'):
        resumen += f" · {r['categoria']}"
    resumen += f" · {r.get('metodo', '—')} · {r.get('motivo', '')}"
    print(resumen)
    if r.get('puntajes'):
        print('  puntajes:', ', '.join(f'{c} {v:g}' for c, v in sorted(r['puntajes'].items(), key=lambda kv: -kv[1])))
    if r['ruta'] == 'clasificar':
        print('  el léxico no decide: el clasificador (clasificador.md) va en el campo prompt_clasificador')
    if a.salida:
        escribir(a.salida, r)


def o_aceptar(a):
    r = aceptar_clasificacion(leer_json(a.ruteo), leer_json(a.clasificacion))
    print(f"ruta {r['ruta']} · {r.get('categoria', '')} · {r['motivo']}" + (f" · HITL: {r['hitl']}" if r.get('hitl') else ''))
    escribir(a.salida or a.ruteo, r)


def o_preparar(a):
    r = leer_json(a.ruteo)
    recientes = a.recientes.split(';') if a.recientes else sujetos_recientes()
    errores = leer_json(a.errores).get('errores') if a.errores else None
    texto = armar_prompt1(r, contenido_de(r), a.motor, recientes, errores)
    print(f"prompt(1) de {r['id']} · categoría {r['categoria']} · {len(texto)} caracteres")
    escribir(a.salida, texto, texto=True)


def o_validar(a):
    r = leer_json(a.ruteo)
    try:
        j = leer_json(a.prompt2)
    except (json.JSONDecodeError, ValueError) as e:
        j, E, A = None, [f'1 · el JSON no se puede leer ({e})'], []
    recientes = a.recientes.split(';') if a.recientes else sujetos_recientes()
    if j is not None:
        E, A = validar_prompt2(r, j, recientes)
    base = {'id': r['id'], 'contenido': r['contenido'], 'categoria': r.get('categoria'), 'metodo': r.get('metodo'),
            'puntajes': r.get('puntajes'), 'confianza': r.get('confianza'), 'evidencia_ruteo': r.get('evidencia'),
            'alternativa': r.get('alternativa'), 'intento': a.intento, 'version': f"prompt1 v1 · lexico v{LEX['version']}",
            'creado': datetime.now().isoformat(timespec='seconds')}
    if j is not None and j.get('estado') in ('NO_ENCAJA', 'CIFRA') and not E:
        ruta = 'fondo' if j['estado'] == 'NO_ENCAJA' else 'diagrama'
        print(f"prompt(1) devolvió {j['estado']}: la ruta pasa a {ruta}")
        salida = {**base, 'estado': j['estado'], 'ruta': ruta, 'motivo_salida': j.get('motivo') or j.get('cita'),
                  'imagen': {'tipo': 'fondo', 'imagen_recorte_fondo': 'optimo'}}
        if a.salida:
            escribir(a.salida, salida)
        return 0
    pedidos, E14 = ensamblar(j) if not E else ([], [])
    E += E14
    for x in A:
        print('  aviso:', x)
    if E:
        print(f'NO PASA ({len(E)} errores):')
        for x in E:
            print('  -', x)
        salida = {**base, 'estado': 'FALLA', 'errores': E, 'avisos': A}
        if a.intento >= 2:
            salida.update(ruta='fondo', motivo_salida='validacion',
                          imagen={'tipo': 'fondo', 'imagen_recorte_fondo': 'optimo'})
            print('  segundo intento fallido: la ruta pasa a fondo (motivo «validacion»)')
        else:
            print('  reintento: python formula/formula.py preparar --ruteo ... --errores <este archivo>')
        if a.salida:
            escribir(a.salida, salida)
        return 1
    salida = {**base, 'estado': 'VALIDADO', 'ruta': 'imagen', 'compara': j['compara'], 'evidencia': j['evidencia'],
              'sujeto': j['sujeto'], 'acentos': j['acentos'], 'motivo': j['motivo'], 'relacion': j['relacion'],
              'no_mostrar': j['no_mostrar'], 'reparo': j.get('reparo') or None, 'avisos': A,
              'alineacion': 'PENDIENTE: la revisan rick-qa o David antes de los créditos (CAND-WLCA-01)',
              'pedidos': pedidos,
              'creditos_por_motor': {m: sum(p['creditos'] for p in pedidos if p['motor'] == m) for m in MOTORES},
              'imagen': {'tipo': 'objeto', 'imagen_objeto_ancla': 'acento'},
              'aviso': 'pedido sin enviar: generar gasta créditos y necesita el OK de David'}
    print(f"VALIDADO · sujeto «{j['sujeto']['compacto']}» · acentos {j['acentos']}")
    print('  créditos si se pide: ' + ', '.join(f'{m} {c}' for m, c in salida['creditos_por_motor'].items()))
    if a.salida:
        escribir(a.salida, salida)
    if a.registrar:
        with REGISTRO.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'id': r['id'], 'categoria': r['categoria'], 'sujeto': j['sujeto']['compacto'],
                                'hash': pedidos[0]['hash_cuerpo'], 'creado': base['creado']},
                               ensure_ascii=False) + '\n')
        print(f'  sujeto anotado en {REGISTRO.name}')
    return 0


def o_regresion(a):
    casos = yaml.safe_load((AQUI / 'fixtures.yaml').read_text(encoding='utf-8'))['casos']
    fallas = 0
    for c in casos:
        r = rutear_pieza(leer_contenido(c['contenido']))
        espera = c['espera']
        ok = all(r.get(k) == v for k, v in espera.items())
        fallas += not ok
        obtenido = ' · '.join(str(r.get(k)) for k in ('ruta', 'categoria', 'metodo') if r.get(k))
        print(f"{'ok   ' if ok else 'FALLA'} {c['nombre'][:52]:52s} {obtenido:34s} {r.get('motivo', '')}")
        if not ok:
            print(f'      esperaba {espera}')
    print(f'{len(casos) - fallas}/{len(casos)} casos como se esperaba')
    if a.ejemplos:
        # Los ejemplos de cada categoría tienen que pasar su propia validación (solo el 16:9, sin la cola).
        print('\nejemplos de categorias.yaml contra la validación del 16:9:')
        for cid, cat in CATS.items():
            cuerpo = cat['ejemplo_prompt2_16_9'].replace(COLA_MG1.strip(), '').strip()
            m = re.search(r'flat teal, the (.+?): (.+?)\. ', cuerpo)
            acentos = re.split(r' and ', m.group(2)) if m else []
            j = {'estado': 'OK', 'categoria': cid, 'compara': 'ejemplo', 'evidencia': ['x'], 'acentos': acentos,
                 'motivo': m.group(1) if m else '', 'relacion': cuerpo.split('. ')[-1], 'no_mostrar': [{'es': 'x', 'en': 'x'}],
                 'sujeto': {'compacto': sujeto_del_ejemplo(cat), 'alargado': 'x'}, 'prompt_16x9': cuerpo,
                 'prompt_21x9': cat['ejemplo_prompt2_21_9'].replace(COLA_MG1.strip(), '').strip()}
            E, _ = validar_prompt2({'categoria': cid, 'titular': 'x', 'bajada': ''}, j, [])
            E = [e for e in E if not e.startswith(('12 ·', '13 ·', '4 · 21:9', '4 · el acento'))]
            print(f"  {'ok   ' if not E else 'FALLA'} {cid}: " + ('; '.join(E) if E else 'pasa'))
    return 1 if fallas else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='orden', required=True)
    s = sub.add_parser('rutear')
    s.add_argument('--contenido', required=True)
    s.add_argument('--salida')
    s = sub.add_parser('aceptar')
    s.add_argument('--ruteo', required=True)
    s.add_argument('--clasificacion', required=True, help='JSON que devolvió el clasificador')
    s.add_argument('--salida', help='por defecto reescribe el ruteo')
    s = sub.add_parser('preparar')
    s.add_argument('--ruteo', required=True)
    s.add_argument('--motor', default='mg1_kit y nb21_sin_kit (mismo cuerpo)')
    s.add_argument('--recientes', help='sujetos de las últimas piezas, separados por «;» (por defecto, registro.jsonl)')
    s.add_argument('--errores', help='el JSON de una validación fallida, para el reintento')
    s.add_argument('--salida', required=True)
    s = sub.add_parser('validar')
    s.add_argument('--ruteo', required=True)
    s.add_argument('--prompt2', required=True, help='el JSON que devolvió prompt(1)')
    s.add_argument('--recientes')
    s.add_argument('--intento', type=int, default=1)
    s.add_argument('--registrar', action='store_true', help='anota el sujeto en registro.jsonl')
    s.add_argument('--salida')
    s = sub.add_parser('regresion')
    s.add_argument('--ejemplos', action='store_true', help='pasa también los ejemplos de cada categoría por la validación')
    a = ap.parse_args()
    sys.exit({'rutear': o_rutear, 'aceptar': o_aceptar, 'preparar': o_preparar, 'validar': o_validar,
              'regresion': o_regresion}[a.orden](a) or 0)


if __name__ == '__main__':
    main()
