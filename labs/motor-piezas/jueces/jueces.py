"""Jueces del motor de piezas: encargos por lente, voto sellado y calibración contra las elecciones de David.

Un juez es un agente que mira las piezas con una sola lente de `rubricas.yaml`. El código mide antes
(UB-3, contraste, objeto en la máscara, turquesa en el recorte) y se lo pasa; el juez no lo rehace.
Cada juez recibe además los criterios de David que tocan su lente (`criterios-david.yaml`).

  preparar   escribe un JSON con un encargo por lente para una galería (para correrlo en un workflow
             de agentes, uno por lente). --criterios-hasta G deja fuera lo aprendido desde G en
             adelante (sirve para medir, sobre galerías pasadas, si los criterios ayudan).
  sellar     guarda los votos en votos/ con la hora y el hash de la rúbrica y de los criterios. Si David
             ya eligió esa galería, solo se acepta como prueba retroactiva (--retro).
  agregar    ordena las opciones con los pesos de cada lente y los vetos.
  elegir     anota la elección de David (elecciones.yaml y decisiones.csv).
  auditar    revisa que ningún juez haya abierto un registro de las elecciones (si lo hizo, su voto no vale).
  calibrar   compara cada voto sellado con lo que eligió David (elecciones.yaml): acierto, posición de
             la elegida y acuerdo por lente. Recalcula pesos.yaml y lista los desacuerdos.

Uso:
  python jueces/jueces.py preparar --galeria G28 --etapas imagen,pieza --salida jueces/encargos/G28.json
  python jueces/jueces.py sellar --galeria G28 --rubrica v2 --votos votos-crudos.json
  python jueces/jueces.py agregar --votos jueces/votos/G28-v2.json
  python jueces/jueces.py calibrar
"""
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import yaml

AQUI = Path(__file__).resolve().parent
LAB = AQUI.parent
CRITERIOS = AQUI / 'criterios-david.yaml'
ELECCIONES = AQUI / 'elecciones.yaml'
INTERACCIONES = AQUI / 'interacciones.jsonl'
PESOS = AQUI / 'pesos.yaml'
VOTOS = AQUI / 'votos'


def leer_yaml(ruta: Path, defecto=None):
    return yaml.safe_load(ruta.read_text(encoding='utf-8')) if ruta.exists() else defecto


def num_galeria(gid: str) -> int:
    return int(re.sub(r'\D', '', gid.split('.')[0]) or 0)


def sha(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()[:12] if ruta.exists() else '-'


# ---------------------------------------------------------------------------------------------- opciones
def opciones(gid: str, seccion: int | None = None):
    """Las opciones entre las que se elige. Con una sola sección (o con --seccion), cada pieza es una
    opción y su número es el de la pieza (1°, 2°…), como lo dice David. Con varias secciones, cada
    sección es una opción (1, 2, 3…) con todas sus piezas."""
    if gid.startswith('M'):
        # una ronda de metáforas en texto (formula/demo/M01-metaforas.json): opciones sin piezas
        ronda = json.loads((LAB / 'formula' / 'demo' / f'{gid}-metaforas.json').read_text(encoding='utf-8'))
        return {'titulo': f"Metáforas para «{ronda['titular']}»", 'descripcion': ronda['premisa']},             [{'id': int(n), 'nombre': o['metafora']['sujeto'], 'piezas': []} for n, o in ronda['opciones'].items()]
    defin = leer_yaml(LAB / 'galerias' / f'{gid}.yaml')
    dir_g = LAB / 'salida' / gid
    piezas = json.loads((dir_g / 'galeria.json').read_text(encoding='utf-8'))['piezas']
    secs, i, por_sec = defin['secciones'], 0, []
    for s in secs:
        n = len(s.get('piezas', []))
        por_sec.append(piezas[i:i + n])
        i += n
    if len(secs) == 1 or seccion:
        k = (seccion or 1) - 1
        pasos = secs[k].get('pasos') or []
        return defin, [{'id': int(re.sub(r'\D', '', p['numero'])), 'nombre': pasos[j] if j < len(pasos) else p['codigo'],
                        'piezas': [p]} for j, p in enumerate(por_sec[k])]
    return defin, [{'id': n, 'nombre': s.get('titulo', f'sección {n}'), 'piezas': por_sec[n - 1],
                    'imagenes': imagenes_de(s.get('contenido'))} for n, s in enumerate(secs, 1)]


def imagenes_de(contenido: str | None) -> list:
    """Las imágenes de Magnific que usa un contenido (principal y apaisada), para las lentes de imagen."""
    if not contenido:
        return []
    c = leer_yaml(LAB / contenido, {}) or {}
    cat = leer_yaml(LAB / 'imagenes.magnific.yaml', {}) or {}
    cat = cat.get('imagenes', cat)
    rutas = leer_yaml(LAB / 'rutas.yaml')
    base = Path(rutas['marca']) / rutas['imagenes_magnific']
    salida = []
    for clave, nombre in [('imagen', 'principal'), ('imagen_ancha', 'apaisada')]:
        ident = c.get(clave)
        if ident in cat:
            region = cat[ident].get('region')
            salida.append(f"{nombre}: {base / cat[ident]['archivo']}" + (f' (se usa la región {region})' if region else ''))
    return salida


def medidas(gid: str, p: dict) -> str:
    """Lo que el código midió en una pieza, en una línea."""
    ficha = json.loads((LAB / 'salida' / gid / 'piezas' / f"{p['codigo']}.json").read_text(encoding='utf-8'))
    utiles = {'contraste_texto', 'contraste_sobre_imagen', 'texto_minimo_movil', 'sin_choques'}
    partes = [p.get('estado', '')]
    partes += [f"{v['regla']}: {v.get('detalle', '')}" for v in ficha['verificaciones']
               if v['regla'] in utiles or not v['ok']]
    partes += [n for n in ficha.get('notas', []) if re.search(r'imagen|objeto|acento|recorte|velo|título|titulo', n)][:6]
    return '; '.join(x for x in partes if x)


# ---------------------------------------------------------------------------------------------- criterios
def criterios_para(lente_completa: str, hasta: str | None):
    """Los criterios de David que tocan una lente, aprendidos antes de la galería `hasta`."""
    datos = leer_yaml(CRITERIOS, {}) or {}
    salida = []
    for c in datos.get('criterios', []):
        lentes = c.get('lentes', [])
        # el juez de predicción recibe todos los criterios; los demás, los de su lente
        if lente_completa != 'eleccion.prediccion' and lente_completa not in lentes and 'todas' not in lentes:
            continue
        if not lentes:
            continue
        # al medir sobre una galería pasada, solo lo aprendido con evidencia toda anterior a ella
        if hasta and num_galeria(c.get('hasta') or c.get('desde') or 'G0') >= num_galeria(hasta):
            continue
        cita = c['evidencia'][0] if c.get('evidencia') else {}
        marca = '[a prueba] ' if c.get('estado') == 'a prueba' else ''
        salida.append(f"- {marca}{c['regla']} ({cita.get('galeria', '')}: «{cita.get('cita', '')}»)")
    return salida


# ---------------------------------------------------------------------------------------------- ejemplos
def ejemplos_para(hasta: str | None, maximo: int = 10) -> list:
    """Las elecciones anteriores de David como ejemplos para el juez de predicción: qué opciones había, cuál
    eligió y con qué palabras. Solo galerías anteriores a `hasta` (al medir sobre el pasado) y las más
    recientes primero."""
    elecciones = leer_yaml(ELECCIONES, {}) or {}
    previas = [g for g in elecciones if not hasta or num_galeria(g) < num_galeria(hasta)]
    salida = []
    for g in sorted(previas, key=num_galeria, reverse=True)[:maximo]:
        e = elecciones[g]
        try:
            defin, ops = opciones(g.split('.')[0], int(g.split('.')[1]) if '.' in g else None)
        except Exception:
            continue
        val = {str(k): v for k, v in (e.get('valoraciones') or {}).items()}
        com = {str(k): v for k, v in (e.get('comentarios') or {}).items()}
        lineas = [f"{g} · {defin.get('titulo', '')}"]
        for o in ops:
            marca = '  ← eligió' if o['id'] in e['elegidas'] else ''
            extra = (f" [valoración {val[str(o['id'])]}]" if str(o['id']) in val else '') + \
                    (f" «{com[str(o['id'])]}»" if str(o['id']) in com and o['id'] not in e['elegidas'] else '')
            lineas.append(f"   {o['id']}: {str(o['nombre'])[:110]}{marca}{extra}")
        lineas.append(f"   David: «{e.get('cita', '')}»")
        salida.append('\n'.join(lineas))
    return salida


# ---------------------------------------------------------------------------------------------- preparar
def preparar(a):
    rub = leer_yaml(Path(a.rubrica) if a.rubrica else AQUI / 'rubricas.yaml')
    defin, ops = opciones(a.galeria, a.seccion)
    dir_g = LAB / 'salida' / a.galeria
    lineas = []
    for o in ops:
        lineas.append(f"Opción {o['id']}: {o['nombre']}")
        lineas += [f'  - imagen {x}' for x in o.get('imagenes', [])]
        for p in o['piezas']:
            lineas.append(f"  - pieza {p['numero']} ({p['formato']}): {dir_g / p['png']} · {medidas(a.galeria, p)}")
    contexto = (f"Galería {a.galeria}: {defin.get('titulo', '')}\n{' '.join(str(defin.get('descripcion', '')).split())}\n"
                f"Hoja con todas las piezas numeradas: {dir_g / '00_preview.jpg'}\n" + '\n'.join(lineas))
    encargos = []
    for etapa in a.etapas.split(','):
        for lente, regla in rub['etapas'][etapa]['lentes'].items():
            if a.lentes and lente not in a.lentes.split(','):
                continue
            crit = [] if a.sin_criterios else criterios_para(f'{etapa}.{lente}', a.criterios_hasta)
            ejem = ejemplos_para(a.criterios_hasta) if etapa == 'eleccion' and a.ejemplos else []
            texto = (f"Eres un juez del motor de piezas de Umbral BIM, con una sola lente: {lente.upper()} (etapa {etapa}).\n"
                     f"Mira: {regla['mira']}.\n"
                     + (f"Vetos (si aparece uno, la opción no sirve): {'; '.join(regla['veto'])}.\n" if regla['veto'] else '')
                     + (f"\nCriterios de David para tu lente. {' '.join(rub['criterios']['regla'].split())}\n"
                        + '\n'.join(crit) + '\n' if crit and 'criterios' in rub else '')
                     + ("\nElecciones anteriores de David (las más recientes primero). Úsalas para entender cómo decide, "
                        "no para copiar la opción por su número:\n" + '\n'.join(ejem) + '\n' if ejem else '')
                     + f"\nEscala: {rub['escala']}. Gravedad: {json.dumps(rub['gravedad'], ensure_ascii=False)}.\n"
                     f"Elige entre las opciones de abajo (no sabes cuál eligió David ni lo que dijeron otros jueces). "
                     f"Mira la hoja numerada y las piezas que necesites con Read. Las medidas son del código: úsalas.\n"
                     f"No llames a Magnific ni gastes créditos, y no escribas archivos. Abre solo los archivos que nombra "
                     f"este encargo: no busques decisiones.csv, elecciones.yaml, criterios-david.yaml, jueces/votos ni "
                     f"otro registro de lo que eligió David (el voto se anula si lo haces).\n"
                     + ("Si tu lente no tiene nada que mirar en esta galería, responde no_aplica true y puntajes vacío.\n"
                        if rub.get('version', 1) >= 2 else '')
                     + f"\n{contexto}\n\nDevuelve: {json.dumps(rub['salida'], ensure_ascii=False)}. En castellano.")
            encargos.append({'galeria': a.galeria, 'seccion': a.seccion, 'etapa': etapa, 'lente': lente,
                             'rubrica': rub.get('version', 1), 'criterios': len(crit), 'ejemplos': len(ejem),
                             'encargo': texto})
    destino = LAB / a.salida
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(encargos, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f"{destino}: {len(encargos)} encargos, {len(ops)} opciones, "
          f"criterios por lente {[e['criterios'] for e in encargos]}")


# ---------------------------------------------------------------------------------------------- sellar
def clave(gid: str, seccion) -> str:
    return f'{gid}.{seccion}' if seccion else gid


def sellar(a):
    elecciones = leer_yaml(ELECCIONES, {}) or {}
    k = clave(a.galeria, a.seccion)
    if k in elecciones and not a.retro:
        raise SystemExit(f'David ya eligió {k}: un voto de ahora no es ciego. Usa --retro si es una prueba retroactiva.')
    votos = json.loads(Path(a.votos).read_text(encoding='utf-8'))
    VOTOS.mkdir(exist_ok=True)
    destino = VOTOS / f'{k}-{a.rubrica}.json'
    if destino.exists() and not a.reemplazar:
        raise SystemExit(f'{destino} ya existe: un voto sellado no se pisa (usa --reemplazar si es a propósito).')
    sello = {'galeria': a.galeria, 'seccion': a.seccion, 'rubrica': a.rubrica, 'retro': bool(a.retro),
             'criterios_hasta': a.criterios_hasta, 'sellado': datetime.now().isoformat(timespec='seconds'),
             'hash_rubrica': sha(Path(a.archivo_rubrica) if a.archivo_rubrica else AQUI / 'rubricas.yaml'),
             'hash_criterios': sha(CRITERIOS) if a.rubrica != 'v1' else '-', 'votos': votos}
    destino.write_text(json.dumps(sello, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'sellado {destino} ({len(votos)} votos)')


# ---------------------------------------------------------------------------------------------- agregar
def vetos_por_lente():
    rubs = [leer_yaml(AQUI / 'rubricas.yaml'), leer_yaml(AQUI / 'historial' / 'rubricas-v1.yaml')]
    salida = {}
    for rub in rubs:
        for etapa in rub['etapas'].values():
            for lente, regla in etapa['lentes'].items():
                salida.setdefault(lente, regla['veto'])
    return salida


def ordenar(votos: list, pesos: dict, camino: str = 'B'):
    """Promedio ponderado por lente (las que aplican) y vetos. Devuelve [(opcion, puntaje, vetada)]."""
    vetos = vetos_por_lente()
    suma, peso_total, vetadas = {}, {}, set()
    for v in votos:
        if not v or v.get('no_aplica') or not v.get('puntajes'):
            continue
        w = float(pesos.get(v['lente'], 1.0))
        for opcion, puntaje in v['puntajes'].items():
            o = str(re.sub(r'\D', '', str(opcion)) or opcion)
            suma[o] = suma.get(o, 0.0) + w * float(puntaje)
            peso_total[o] = peso_total.get(o, 0.0) + w
        for h in v.get('hallazgos', []):
            if h.get('gravedad') == 'alta' and vetos.get(v['lente']):
                o = str(re.sub(r'\D', '', str(h.get('opcion', ''))))
                if o:
                    vetadas.add(o)
    orden = sorted(((o, suma[o] / peso_total[o]) for o in suma), key=lambda x: -x[1])
    return [(o, s, o in vetadas) for o, s in orden]


def agregar(a):
    sello = json.loads(Path(a.votos).read_text(encoding='utf-8'))
    votos = sello['votos'] if isinstance(sello, dict) else sello
    pesos = (leer_yaml(PESOS, {}) or {}).get('pesos', {})
    orden = ordenar(votos, pesos)
    for o, s, vetada in orden:
        print(f"opción {o:>3s}  {s:5.2f} {'no sirve (veto)' if vetada else ''}")
    validas = [o for o, _, v in orden if not v]
    print(f"elegida por los jueces: {validas[0] if validas else 'ninguna'}")


def rangos(valores: list) -> list:
    orden = sorted(range(len(valores)), key=lambda i: valores[i])
    r = [0.0] * len(valores)
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and valores[orden[j + 1]] == valores[orden[i]]:
            j += 1
        for k in range(i, j + 1):
            r[orden[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x: list, y: list):
    """Correlación de rangos entre los puntajes de los jueces y la valoración de David (−1 a 1)."""
    if len(x) < 3 or len(set(y)) < 2 or len(set(x)) < 2:
        return None
    rx, ry = rangos(x), rangos(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 2) if den else None


# ---------------------------------------------------------------------------------------------- calibrar
def calibrar(a):
    elecciones = leer_yaml(ELECCIONES, {}) or {}
    pesos_actuales = (leer_yaml(PESOS, {}) or {}).get('pesos', {})
    filas, por_lente, desacuerdos = [], {}, []
    for ruta in sorted(VOTOS.glob('*.json')):
        sello = json.loads(ruta.read_text(encoding='utf-8'))
        k = clave(sello['galeria'], sello.get('seccion'))
        if k not in elecciones:
            continue
        elegidas = {str(x) for x in elecciones[k]['elegidas']}
        # las pruebas retroactivas y la v1 se miden sin pesos: los pesos salen de esos mismos votos
        orden = ordenar(sello['votos'], {} if sello['rubrica'] == 'v1' or sello.get('retro') else pesos_actuales)
        validas = [o for o, _, v in orden if not v]
        top = validas[0] if validas else None
        rango = next((i + 1 for i, o in enumerate(validas) if o in elegidas), None)
        val = {str(o): v for o, v in (elecciones[k].get('valoraciones') or {}).items()}
        comunes = [(s, val[o]) for o, s, _ in orden if o in val]
        rho = spearman([c[0] for c in comunes], [c[1] for c in comunes]) if comunes else None
        filas.append({'galeria': k, 'rubrica': sello['rubrica'], 'retro': sello.get('retro'),
                      'opciones': len(orden), 'elegida_david': '+'.join(sorted(elegidas)), 'top_jueces': top,
                      'acierto': int(top in elegidas), 'rango_elegida': rango or '',
                      'rho_valoracion': '' if rho is None else rho})
        for v in sello['votos']:
            if not v or v.get('no_aplica') or not v.get('mejor'):
                continue
            mejor = str(re.sub(r'\D', '', str(v['mejor'])))
            d = por_lente.setdefault((sello['rubrica'], v['lente']), [0, 0])
            d[0] += int(mejor in elegidas)
            d[1] += 1
        if top not in elegidas:
            desacuerdos.append({'galeria': k, 'rubrica': sello['rubrica'], 'jueces': top, 'david': sorted(elegidas),
                                'cita': elecciones[k].get('cita', ''),
                                'resumenes': {v['lente']: v.get('resumen', '') for v in sello['votos']
                                              if v and not v.get('no_aplica')}})
    if not filas:
        print('no hay votos sellados con elección de David todavía')
        return
    with (AQUI / 'calibracion.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"{'galería':9s} {'rúbrica':7s} {'David':6s} {'jueces':6s} acierto  posición")
    for r in filas:
        print(f"{r['galeria']:9s} {r['rubrica']:12s} {r['elegida_david']:6s} {str(r['top_jueces']):6s} "
              f"{'sí' if r['acierto'] else 'no':7s}  {r['rango_elegida']}/{r['opciones']}"
              + (f"  ρ con su valoración {r['rho_valoracion']}" if r['rho_valoracion'] != '' else ''))
    resumen = {}
    for r in filas:
        d = resumen.setdefault(r['rubrica'], {'n': 0, 'aciertos': 0, 'rangos': []})
        d['n'] += 1
        d['aciertos'] += r['acierto']
        if r['rango_elegida']:
            d['rangos'].append(r['rango_elegida'])
    print()
    for rub, d in sorted(resumen.items()):
        medio = sum(d['rangos']) / len(d['rangos']) if d['rangos'] else 0
        print(f"rúbrica {rub}: {d['aciertos']}/{d['n']} aciertos; la elegida de David queda en promedio en el puesto {medio:.2f}")
    print('\nacuerdo por lente (la mejor de la lente es la de David):')
    for (rub, lente), (ok, n) in sorted(por_lente.items()):
        print(f"  {rub} {lente:12s} {ok}/{n}")
    # pesos: acuerdo suavizado de cada lente de la rúbrica vigente, normalizado a promedio 1
    vigente = f"v{leer_yaml(AQUI / 'rubricas.yaml').get('version', 1)}"
    crudos = {lente: (ok + 1) / (n + 2) for (rub, lente), (ok, n) in por_lente.items() if rub == vigente}
    if crudos and not a.sin_pesos:
        media = sum(crudos.values()) / len(crudos)
        pesos = {lente: round(x / media, 2) for lente, x in sorted(crudos.items())}
        PESOS.write_text(yaml.safe_dump({'rubrica': vigente, 'calculado': datetime.now().isoformat(timespec='seconds'),
                                         'regla': 'acuerdo suavizado (aciertos+1)/(n+2) de cada lente, normalizado a promedio 1',
                                         'pesos': pesos}, allow_unicode=True, sort_keys=False), encoding='utf-8')
        print(f'\npesos.yaml ({vigente}): {pesos}')
    (AQUI / 'desacuerdos.json').write_text(json.dumps(desacuerdos, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{len(desacuerdos)} desacuerdos en jueces/desacuerdos.json (base para ajustar criterios o lentes)')


# ---------------------------------------------------------------------------------------------- elegir
def elegir(a):
    """Anota una respuesta de David a una galería. Guarda la elección y, si las hay, la valoración de cada
    opción (2 la mejor, 1 bien, 0 casi, -1 no sirve o le falta algo) y su comentario por opción. Escribe
    elecciones.yaml (para calibrar), decisiones.csv (comentario por pieza) e interacciones.jsonl (el mensaje
    entero, para volver a aprender de él)."""
    elecciones = leer_yaml(ELECCIONES, {}) or {}
    k = clave(a.galeria, a.seccion)
    elegidas = [int(x) for x in a.elegidas.split(',')]
    _, ops = opciones(a.galeria, a.seccion)
    por_id = {o['id']: o for o in ops}
    if not all(e in por_id for e in elegidas):
        raise SystemExit(f'opciones {elegidas} no están en {k}: opciones {sorted(por_id)}')
    valoraciones = {}
    for parte in (a.valoraciones or '').split(','):
        if ':' in parte:
            ids, nivel = parte.split(':')
            ini, _, fin = ids.partition('-')
            for o in range(int(ini), int(fin or ini) + 1):
                valoraciones[o] = int(nivel)
    comentarios = {int(o): c for o, c in json.loads(a.comentarios).items()} if a.comentarios else {}
    fecha = a.fecha or datetime.now().date().isoformat()
    registro = {'elegidas': elegidas, 'fecha': fecha, 'cita': a.cita}
    if valoraciones:
        registro['valoraciones'] = valoraciones
    if comentarios:
        registro['comentarios'] = comentarios
    elecciones[k] = registro
    texto = ELECCIONES.read_text(encoding='utf-8') if ELECCIONES.exists() else ''
    cabecera = ''.join(l for l in texto.splitlines(keepends=True) if l.startswith('#'))
    cuerpo = ''.join(f"{g}: {json.dumps(v, ensure_ascii=False, default=str)}\n" for g, v in elecciones.items())
    ELECCIONES.write_text(cabecera + cuerpo, encoding='utf-8')
    ruta = LAB / 'decisiones.csv'
    filas = list(csv.DictReader(ruta.open(encoding='utf-8')))
    por_codigo = {}
    for o in ops:
        nota = comentarios.get(o['id']) or (a.cita if o['id'] in elegidas else '')
        if o['id'] in elegidas and comentarios.get(o['id']):
            nota = f"{a.cita} · {comentarios[o['id']]}"
        for p in o['piezas']:
            if nota:
                por_codigo[p['codigo']] = nota
    for f in filas:
        if f['codigo'] in por_codigo:
            f['comentario_david'], f['fecha'] = por_codigo[f['codigo']], fecha
    with ruta.open('w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    if a.texto:
        with INTERACCIONES.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps({'fecha': fecha, 'galeria': k, 'tipo': 'eleccion', 'texto': a.texto,
                                 'elegidas': elegidas, 'valoraciones': valoraciones}, ensure_ascii=False) + '\n')
    print(f'{k}: elegidas {elegidas}; valoraciones {valoraciones or "—"}; {len(por_codigo)} piezas con comentario')


# ---------------------------------------------------------------------------------------------- auditar
RESPUESTAS = re.compile(r'decisiones\.csv|elecciones\.yaml|criterios-david|desacuerdos\.json|calibracion\.csv|jueces[/\\]+votos')


def auditar(a):
    """Revisa las transcripciones de una tanda de jueces: un juez que abrió un registro de lo que eligió David
    deja de ser ciego y su voto se descarta."""
    contaminados = []
    for ruta in sorted(Path(a.transcripciones).glob('agent-*.jsonl')):
        usos = re.findall(r'"(?:file_path|command|pattern|path)":"([^"]{0,400})', ruta.read_text(encoding='utf-8', errors='ignore'))
        malos = [u for u in usos if RESPUESTAS.search(u)]
        if malos:
            meta = ruta.with_suffix('.meta.json')
            nombre = json.loads(meta.read_text(encoding='utf-8')).get('description', ruta.stem) if meta.exists() else ruta.stem
            contaminados.append(nombre)
            print(f'CONTAMINADO {nombre}: {len(malos)} lecturas, p. ej. {malos[0][:100]}')
    print(f'{len(contaminados)} jueces contaminados' if contaminados else 'ningún juez abrió registros de las elecciones de David')
    return contaminados


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='orden', required=True)
    p = sub.add_parser('preparar')
    p.add_argument('--galeria', required=True)
    p.add_argument('--seccion', type=int, help='elegir entre las piezas de una sección (galerías con varias)')
    p.add_argument('--etapas', default='pieza', help='imagen, pieza, campana, separadas por comas')
    p.add_argument('--lentes', help='lista separada por comas; por defecto todas las de las etapas')
    p.add_argument('--rubrica', help='otro archivo de rúbrica (por ejemplo historial/rubricas-v1.yaml)')
    p.add_argument('--sin-criterios', action='store_true')
    p.add_argument('--criterios-hasta', help='solo criterios aprendidos antes de esta galería')
    p.add_argument('--ejemplos', action='store_true', help='el juez de predicción ve las elecciones anteriores de David')
    p.add_argument('--salida', required=True)
    s = sub.add_parser('sellar')
    s.add_argument('--galeria', required=True)
    s.add_argument('--seccion', type=int)
    s.add_argument('--rubrica', required=True, help='etiqueta: v1, v2…')
    s.add_argument('--archivo-rubrica')
    s.add_argument('--criterios-hasta')
    s.add_argument('--votos', required=True)
    s.add_argument('--retro', action='store_true', help='prueba sobre una galería que David ya eligió')
    s.add_argument('--reemplazar', action='store_true')
    g = sub.add_parser('agregar')
    g.add_argument('--votos', required=True)
    e = sub.add_parser('elegir')
    e.add_argument('--galeria', required=True)
    e.add_argument('--seccion', type=int)
    e.add_argument('--elegidas', required=True, help='números de opción separados por comas')
    e.add_argument('--cita', required=True, help='lo que dijo David, literal')
    e.add_argument('--valoraciones', help='opción:nivel separadas por comas, con rangos (1-3:-1,4:1,6:2)')
    e.add_argument('--comentarios', help='JSON {opción: cita literal de David sobre esa opción}')
    e.add_argument('--texto', help='el mensaje entero de David, literal (va a interacciones.jsonl)')
    e.add_argument('--fecha')
    u = sub.add_parser('auditar')
    u.add_argument('--transcripciones', required=True, help='carpeta con los agent-*.jsonl de la tanda')
    c = sub.add_parser('calibrar')
    c.add_argument('--sin-pesos', action='store_true', help='no reescribe pesos.yaml')
    a = ap.parse_args()
    {'preparar': preparar, 'sellar': sellar, 'agregar': agregar, 'elegir': elegir, 'auditar': auditar, 'calibrar': calibrar}[a.orden](a)


if __name__ == '__main__':
    main()
