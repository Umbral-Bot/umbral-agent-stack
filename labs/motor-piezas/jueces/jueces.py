"""Jueces del motor de piezas: arma los encargos por lente y agrega los votos.

Un juez es un agente que mira las piezas con una sola lente de `rubricas.yaml`. El código mide
antes (UB-3, objeto en la máscara, turquesa en el recorte) y se lo pasa; el juez no lo rehace.

  preparar  escribe un JSON con un encargo por lente para las piezas de una galería (para
            correrlo en un workflow de agentes, uno por lente).
  agregar   suma los votos, aplica los vetos y elige.

Uso:
  python jueces/jueces.py preparar --galeria G27 --etapa pieza --salida jueces/encargos-G27.json
  python jueces/jueces.py agregar --votos votos-G27.json --camino B
"""
import argparse
import json
from pathlib import Path

import yaml

LAB = Path(__file__).resolve().parent.parent
RUBRICAS = yaml.safe_load((Path(__file__).parent / 'rubricas.yaml').read_text(encoding='utf-8'))


def preparar(a):
    etapa = RUBRICAS['etapas'][a.etapa]
    dir_g = LAB / 'salida' / a.galeria
    piezas = json.loads((dir_g / 'galeria.json').read_text(encoding='utf-8'))['piezas']
    medidas = []
    for p in piezas:
        ficha = json.loads((dir_g / 'piezas' / f"{p['codigo']}.json").read_text(encoding='utf-8'))
        avisos = [x['regla'] for x in ficha['verificaciones'] if not x['ok']]
        notas = [n for n in ficha['notas'] if 'imagen' in n or 'objeto' in n or 'acento' in n or 'recorte' in n]
        medidas.append(f"- {p['codigo']} ({p['formato']}): {p['estado']}; avisos {avisos or 'ninguno'}; {'; '.join(notas)}; "
                       f"archivo {dir_g / p['png']}")
    encargos = []
    for lente, regla in etapa['lentes'].items():
        if a.lentes and lente not in a.lentes.split(','):
            continue
        texto = (f"Eres un juez del motor de piezas de Umbral BIM, con una sola lente: {lente.upper()}.\n"
                 f"Mira: {regla['mira']}.\n"
                 + (f"Vetos (si aparece uno, la opción no sirve): {'; '.join(regla['veto'])}.\n" if regla['veto'] else '')
                 + f"Escala: {RUBRICAS['escala']}. Gravedad: {json.dumps(RUBRICAS['gravedad'], ensure_ascii=False)}.\n"
                 f"No llames a Magnific ni gastes créditos; solo lee las imágenes (Read). Las medidas son del código: úsalas.\n"
                 f"Piezas y medidas:\n" + '\n'.join(medidas) + "\n"
                 f"Devuelve: {json.dumps(RUBRICAS['salida'], ensure_ascii=False)}. En castellano.")
        encargos.append({'lente': lente, 'etapa': a.etapa, 'galeria': a.galeria, 'encargo': texto})
    destino = LAB / a.salida
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(encargos, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{destino}: {len(encargos)} encargos ({", ".join(e["lente"] for e in encargos)})')


def agregar(a):
    votos = json.loads(Path(a.votos).read_text(encoding='utf-8'))
    total, vetadas = {}, set()
    vetos = {lente: regla['veto'] for etapa in RUBRICAS['etapas'].values() for lente, regla in etapa['lentes'].items()}
    for v in votos:
        for opcion, puntaje in v['puntajes'].items():
            total[opcion] = total.get(opcion, 0) + puntaje
        for h in v.get('hallazgos', []):
            if h.get('gravedad') == 'alta' and vetos.get(v['lente']):
                for opcion in total:
                    if opcion.lower() in h.get('donde', '').lower():
                        vetadas.add(opcion)
    orden = sorted(total.items(), key=lambda kv: -kv[1])
    desempate = 'contenido' if a.camino == 'B' else 'marca'
    for opcion, puntos in orden:
        estado = 'no sirve (veto)' if opcion in vetadas else ''
        print(f'{opcion:8s} {puntos:5.1f} {estado}')
    validas = [o for o, _ in orden if o not in vetadas]
    print(f'elegida: {validas[0] if validas else "ninguna"} (desempate por la lente {desempate})')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='orden', required=True)
    p = sub.add_parser('preparar')
    p.add_argument('--galeria', required=True)
    p.add_argument('--etapa', choices=list(RUBRICAS['etapas']), required=True)
    p.add_argument('--lentes', help='lista separada por comas; por defecto todas las de la etapa')
    p.add_argument('--salida', required=True)
    g = sub.add_parser('agregar')
    g.add_argument('--votos', required=True)
    g.add_argument('--camino', choices=['A', 'B'], default='B')
    a = ap.parse_args()
    preparar(a) if a.orden == 'preparar' else agregar(a)


if __name__ == '__main__':
    main()
