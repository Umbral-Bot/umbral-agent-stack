#!/usr/bin/env python3
"""Verificador del gate de 24 horas.

Reconstruye los ciclos desde los registros DURABLES (`ops_log.jsonl`), sin
depender de ningún recolector en ejecución. La primera versión del recolector
contó como ciclos dos ejecuciones manuales del propio hilo y declaró el gate
superado con uno solo real; por eso este verificador no confía en nada que no
esté escrito en el registro.

    python3 verificar-gate-24h.py --desde 2026-09-19T14:00:00Z [--horas 24]
    python3 verificar-gate-24h.py --autoprueba

`--autoprueba` comprueba el verificador contra registros sintéticos antes de
usarlo para juzgar nada. Se añadió después de descubrir que el ensayo sintético
llevaba un día declarando un paso en verde con una comprobación que había dejado
de mirar lo que creía mirar: un instrumento de validación que se rompe en
silencio tiene el mismo defecto que el monitor al que vigila.

Exit 0 si el gate pasa, 1 si no.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

CADENCIA_MIN = 30          # health-check corre cada 30 minutos
TOLERANCIA_MIN = 4         # margen para considerar que un ciclo es "de cron"
HUECO_MAX_MIN = 45         # más que esto entre ciclos consecutivos = ciclo omitido

# La cadencia NO se copia aquí: se lee de la propia biblioteca del monitor. Una
# copia en este archivo se desincroniza en cuanto cambie el tope, y entonces el
# verificador acusaría de "avisar antes de tiempo" a un monitor que respeta su
# cadencia. Es el mismo error que tenía el ensayo sintético: un instrumento que
# duplica lo que debería leer.
LIB = Path(__file__).resolve().parent / "lib" / "umbral_alerting.sh"


def _constante(nombre: str, por_defecto: int) -> int:
    try:
        for linea in LIB.read_text(encoding="utf-8").splitlines():
            if linea.startswith(f"{nombre}="):
                return int(linea.split(":-")[1].split("}")[0])
    except Exception:
        pass
    return por_defecto


COOLDOWN_S = _constante("UMBRAL_ALERT_COOLDOWN_S", 3600)      # primera ventana
BACKOFF_MAX_S = _constante("UMBRAL_ALERT_BACKOFF_MAX_S", 82800)  # tope


def ventana(reavisos: int) -> int:
    """Cadencia documentada del retroceso: 1 h, 2 h, 4 h, 8 h, 16 h, tope 24 h.
    Debe coincidir con `umbral_alert_window` de scripts/vps/lib/umbral_alerting.sh."""
    v = COOLDOWN_S
    for _ in range(max(0, reavisos)):
        if v >= BACKOFF_MAX_S:
            break
        v *= 2
    return min(v, BACKOFF_MAX_S)


def momento(ts: str) -> datetime:
    value = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("la marca temporal debe incluir zona horaria")
    return value.astimezone(timezone.utc)


KINDS = {"release_deploy", "health_check", "canary_inference", "monitor_alert",
         "monitor_alert_failed", "monitor_alert_suppressed", "monitor_alert_simulado"}


class RegistroInvalido(ValueError):
    """No se puede emitir un veredicto con una fuente ilegible o inestable."""


def indice_rotacion(path: Path, active: Path) -> int | None:
    """Solo la familia numérica del registro declara precedencia entre fuentes."""
    if path == active:
        return 0
    prefix = active.name + "."
    if path.name.startswith(prefix):
        suffix = path.name[len(prefix):].removesuffix(".gz")
        if suffix.isdigit() and int(suffix) > 0:
            return int(suffix)
    return None


def ordenar_registro(records: dict, sources: list, active: Path) -> list[dict]:
    """Conserva el orden de línea de las alertas empatadas, aun al deduplicar.

    Una ocurrencia se identifica por contenido y ordinal dentro de su fuente.
    Las copias compartidas dan anclas de orden; las rotaciones numéricas ordenan
    las partes exclusivas. Un empate externo sin orden verificable solo bloquea
    si afecta al estado de un mismo monitor, no por eventos independientes.
    """
    buckets: dict = {}
    for path, sequence in sources:
        for node in sequence:
            ts = momento(records[node]["ts"])
            buckets.setdefault(ts, {}).setdefault(path, []).append(node)
    result = []
    for ts, per_source in sorted(buckets.items()):
        nodes = dict.fromkeys(node for sequence in per_source.values() for node in sequence)
        edges = {node: set() for node in nodes}
        monitors: dict = {}
        for node in nodes:
            event = records[node]
            if event["kind"] == "monitor_alert":
                monitors.setdefault(event.get("monitor", "?"), []).append(node)
        for monitor, members in monitors.items():
            member_set = set(members)
            sequences = {path: [n for n in seq if n in member_set]
                         for path, seq in per_source.items()}
            for sequence in sequences.values():
                for before, after in zip(sequence, sequence[1:]):
                    edges[before].add(after)
            for old_path, old in sequences.items():
                old_index = indice_rotacion(old_path, active)
                for new_path, new in sequences.items():
                    new_index = indice_rotacion(new_path, active)
                    if old_index is None or new_index is None or old_index <= new_index:
                        continue
                    # No ordenar de nuevo las copias solapadas: sus líneas ya
                    # aportan las relaciones. Solo unir los extremos exclusivos.
                    old_only = [n for n in old if n not in set(new)]
                    new_only = [n for n in new if n not in set(old)]
                    if old_only and new_only:
                        edges[old_only[-1]].add(new_only[0])
            reachable = {}
            for node in members:
                seen, pending = set(), list(edges[node])
                while pending:
                    next_node = pending.pop()
                    if next_node not in seen:
                        seen.add(next_node)
                        pending.extend(edges[next_node])
                if node in seen:
                    raise RegistroInvalido(f"orden contradictorio de alertas: {ts.isoformat()}, monitor {monitor}")
                reachable[node] = seen
            for i, node in enumerate(members):
                for other in members[i + 1:]:
                    if other not in reachable[node] and node not in reachable[other]:
                        raise RegistroInvalido(f"orden ambiguo entre fuentes: {ts.isoformat()}, monitor {monitor}")
        # Orden estable para el resto: entre monitores/eventos independientes
        # los empates no modifican los criterios del gate.
        incoming = Counter(after for children in edges.values() for after in children)
        while nodes:
            node = next(n for n in nodes if not incoming[n])
            result.append(records[node])
            del nodes[node]
            for after in edges[node]:
                incoming[after] -= 1
    return result


@dataclass
class Registro:
    """Snapshot de fuentes activas/rotadas, leído una vez, sin modificar archivos.

    La primera ruta identifica el activo; las demás pueden ser copias rotadas.
    Elimina copias del MISMO evento entre fuentes, conservando la multiplicidad
    máxima dentro de una fuente. Dos entregas idénticas en un solo archivo siguen
    siendo dos: deduplicar el transporte no debe ocultar un aviso real duplicado.
    """

    paths: tuple[Path, ...]
    events: list[dict] = field(init=False, default_factory=list)
    manifests: list[dict] = field(init=False, default_factory=list)
    duplicates: int = field(init=False, default=0)

    def __post_init__(self):
        maximum: Counter[str] = Counter()
        unique_paths = sorted({p.expanduser().resolve() for p in self.paths}, key=str)
        if not unique_paths:
            raise RegistroInvalido("no hay fuentes de registro")
        active = self.paths[0].expanduser().resolve()
        records, sources = {}, []
        for path in unique_paths:
            try:
                with path.open("rb") as source:
                    before = os.fstat(source.fileno())
                    raw = source.read()
                    after = os.fstat(source.fileno())
                current = path.stat()
                identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
                if identity(before) != identity(after) or identity(after) != identity(current):
                    raise RegistroInvalido(f"fuente cambió durante la lectura: {path}")
                stream = gzip.GzipFile(fileobj=io.BytesIO(raw)) if path.suffix == ".gz" else io.BytesIO(raw)
                counts: Counter[str] = Counter()
                sequence = []
                with io.TextIOWrapper(stream, encoding="utf-8") as text:
                    for number, line in enumerate(text, 1):
                        if not line.strip():
                            continue
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise RegistroInvalido(f"JSON inválido: {path}, línea {number}") from exc
                        if not isinstance(event, dict) or event.get("kind") not in KINDS:
                            continue
                        try:
                            momento(event["ts"])
                        except (KeyError, ValueError, TypeError, AttributeError) as exc:
                            raise RegistroInvalido(f"timestamp inválido: {path}, línea {number}") from exc
                        key = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                        counts[key] += 1
                        node = (key, counts[key])
                        records[node] = event
                        sequence.append(node)
                removed = sum(min(count, maximum[key]) for key, count in counts.items())
                self.duplicates += removed
                for key, count in counts.items():
                    maximum[key] = max(maximum[key], count)
                sources.append((path, sequence))
                self.manifests.append({"path": str(path), "bytes": len(raw),
                                       "sha256": hashlib.sha256(raw).hexdigest(),
                                       "relevant_events": sum(counts.values()),
                                       "overlap_removed": removed,
                                       "rotation_index": indice_rotacion(path, active)})
            except (OSError, EOFError, UnicodeError) as exc:
                raise RegistroInvalido(f"fuente ilegible: {path} ({type(exc).__name__})") from exc
        self.events = ordenar_registro(records, sources, active)

    def __str__(self):
        return ", ".join(str(p) for p in self.paths)


def como_registro(ops: Path | Registro) -> Registro:
    return ops if isinstance(ops, Registro) else Registro((ops,))


def leer(p: Path | Registro, desde: str, hasta: str, kinds: set[str]) -> list[dict]:
    start, end = momento(desde), momento(hasta)
    return [event for event in como_registro(p).events
            if event["kind"] in kinds and start <= momento(event["ts"]) <= end]


def es_de_cron(ts: str) -> bool:
    try:
        mm = int(ts[14:16])
    except Exception:
        return False
    return mm <= TOLERANCIA_MIN or abs(mm - CADENCIA_MIN) <= TOLERANCIA_MIN


def clasificar_alertas(alertas: list[dict], fallidas: list[dict]) -> tuple[list[dict], list[str]]:
    """Separa los avisos REALES PREVISTOS por el retroceso de los que no lo son.

    Un aviso no es correcto solo por existir: tiene que tocarle. Se reconstruye
    el estado del monitor tal y como lo lleva la biblioteca y se decide, para
    cada aviso entregado, si le correspondía:

      - `previsto`   : estado nuevo, o venció la ventana que le tocaba
      - `fuera_de_cadencia` : llegó antes de que venciera su ventana
      - `duplicado`  : mismo monitor y misma huella dentro de la ventana en curso
      - `no_entregado` : se intentó y no salió (van aparte, en `fallidas`)
    """
    detalle: list[dict] = []
    problemas: list[str] = []
    estado: dict[str, tuple[str, datetime, int]] = {}
    for e in sorted(alertas, key=lambda x: momento(x["ts"])):
        mon = e.get("monitor", "?")
        info = e.get("severity") == "info"
        clave = f"{mon}.info" if info else mon
        fp = e.get("fingerprint", "")
        ts = momento(e["ts"])
        n = e.get("reavisos")
        prev = estado.get(clave)
        fila = {"ts": e["ts"], "monitor": mon, "severidad": e.get("severity", ""),
                "reavisos": n, "huella": fp[:12]}
        if prev and prev[0] == fp:
            exigida = ventana(prev[2])
            transcurrido = (ts - prev[1]).total_seconds()
            fila["exigia_h"] = round(exigida / 3600, 1)
            fila["transcurrido_h"] = round(transcurrido / 3600, 2)
            if transcurrido < exigida:
                fila["clase"] = "duplicado" if transcurrido < 60 else "fuera_de_cadencia"
                problemas.append(
                    f"{e['ts']} {clave}: {fila['clase']} — reavisó a las "
                    f"{transcurrido/3600:.1f} h cuando la cadencia exigía {exigida/3600:.0f} h")
            else:
                fila["clase"] = "previsto"
            if n is not None and n != prev[2] + 1:
                problemas.append(
                    f"{e['ts']} {clave}: el contador de reavisos pasó de {prev[2]} a {n}")
            n_nuevo = n if n is not None else prev[2] + 1
        else:
            fila["clase"] = "previsto"
            fila["motivo"] = "estado nuevo"
            if n not in (None, 0):
                problemas.append(
                    f"{e['ts']} {clave}: estado nuevo pero el contador empieza en {n}")
            n_nuevo = 0
        detalle.append(fila)
        estado[clave] = (fp, ts, n_nuevo)
        if info:
            estado.pop(mon, None)      # la recuperación cierra el incidente

    for e in sorted(fallidas, key=lambda x: x.get("ts", "")):
        detalle.append({"ts": e["ts"], "monitor": e.get("monitor", "?"),
                        "severidad": e.get("severity", ""), "clase": "no_entregado",
                        "motivo": e.get("motivo", ""), "huella": str(e.get("fingerprint", ""))[:12]})
    return detalle, problemas


def revisar_cadencia(alertas: list[dict]) -> list[str]:
    """Los avisos REALES deben respetar la cadencia documentada.

    Se simula el estado del monitor tal y como lo lleva la biblioteca: la clave
    es el monitor (con sufijo .info para los avisos de recuperación), un estado
    distinto reinicia el contador, y un aviso de recuperación cierra el
    incidente y por tanto borra el estado de fallo.
    """
    problemas: list[str] = []
    estado: dict[str, tuple[str, datetime, int]] = {}
    for e in alertas:
        mon = e.get("monitor", "?")
        info = e.get("severity") == "info"
        clave = f"{mon}.info" if info else mon
        fp = e.get("fingerprint", "")
        ts = momento(e["ts"])
        n = e.get("reavisos")
        prev = estado.get(clave)
        if prev and prev[0] == fp:
            exigida = ventana(prev[2])
            transcurrido = (ts - prev[1]).total_seconds()
            if transcurrido < exigida:
                problemas.append(
                    f"{e['ts']} {clave}: reavisó a los {transcurrido/3600:.1f} h "
                    f"cuando la cadencia exigía {exigida/3600:.0f} h")
            if n is not None and n != prev[2] + 1:
                problemas.append(
                    f"{e['ts']} {clave}: el contador de reavisos pasó de {prev[2]} a {n}")
            n_nuevo = n if n is not None else prev[2] + 1
        else:
            if n not in (None, 0):
                problemas.append(
                    f"{e['ts']} {clave}: estado nuevo pero el contador empieza en {n}")
            n_nuevo = 0
        estado[clave] = (fp, ts, n_nuevo)
        if info:
            estado.pop(mon, None)      # la recuperación cierra el incidente
    return problemas


def ultimo_despliegue(ops: Path | Registro, release: str) -> str | None:
    """Instante del último despliegue de ese release, según el propio registro."""
    timestamps = [e["ts"] for e in como_registro(ops).events
                  if e["kind"] == "release_deploy" and e.get("sha") == release]
    return max(timestamps, key=momento) if timestamps else None


def evaluar(ops: Path | Registro, desde: str, horas: float, release: str, silencioso: bool = False) -> list[str]:
    ops = como_registro(ops)
    t1 = momento(desde) + timedelta(hours=horas)
    hasta = t1.strftime("%Y-%m-%dT%H:%M:%SZ")

    hc = [d for d in leer(ops, desde, hasta, {"health_check"}) if es_de_cron(d.get("ts", ""))]
    can = [d for d in leer(ops, desde, hasta, {"canary_inference"}) if es_de_cron(d.get("ts", ""))]
    alertas = leer(ops, desde, hasta, {"monitor_alert"})
    fallidas = leer(ops, desde, hasta, {"monitor_alert_failed"})
    suprimidas = leer(ops, desde, hasta, {"monitor_alert_suppressed"})

    di = print if not silencioso else (lambda *a, **k: None)
    di(f"ventana         : {desde} .. {hasta}  ({horas} h)")
    di(f"release exigido : {release}")
    di(f"registro        : {ops}")
    di("")

    fallos: list[str] = []

    # 1. ciclos esperados vs observados
    esperados = int(horas * 60 / CADENCIA_MIN)
    di(f"1. ciclos de health-check: {len(hc)} observados, ~{esperados} esperados")
    if len(hc) < esperados - 1:     # margen de 1 por bordes de ventana
        fallos.append(f"faltan ciclos: {len(hc)} de ~{esperados}")

    # 2. huecos: ningún ciclo omitido
    huecos = []
    for x, y in zip(hc, hc[1:]):
        gap = (momento(y["ts"]) - momento(x["ts"])).total_seconds() / 60
        if gap > HUECO_MAX_MIN:
            huecos.append(f"{x['ts']} -> {y['ts']} ({gap:.0f} min)")
    di(f"2. huecos > {HUECO_MAX_MIN} min: {len(huecos)}")
    for h in huecos:
        di(f"     {h}")
    if huecos:
        fallos.append(f"{len(huecos)} ciclo(s) omitido(s)")

    # 3. todos desde el release correcto
    otros = [d for d in hc + can + alertas if d.get("release") != release]
    di(f"3. eventos desde otro release: {len(otros)}")
    for d in otros[:5]:
        di(f"     {d.get('ts')} kind={d.get('kind')} release={str(d.get('release'))[:22]}")
    if otros:
        fallos.append(f"{len(otros)} evento(s) desde un release distinto")

    # 4. cero falsas alarmas
    malos = [d for d in hc if d.get("status") != "ok"]
    di(f"4. ciclos con status != ok: {len(malos)}")
    for d in malos[:5]:
        di(f"     {d.get('ts')} status={d.get('status')} detalle={str(d.get('detail'))[:90]}")
    if malos:
        fallos.append(f"{len(malos)} ciclo(s) con alarma")

    # 5. canario estructuralmente correcto, con proveedor y fallback registrados
    can_mal = [d for d in can if d.get("status") not in ("ok", "ok_sin_token")]
    sin_prov = [d for d in can if not d.get("provider") or d.get("provider") == "desconocido"]
    sin_fb = [d for d in can if "fallback_used" not in d]
    sin_token = [d for d in can if d.get("status") == "ok_sin_token"]
    di(f"5. canario: {len(can)} corridas, {len(can_mal)} con fallo estructural, "
       f"{len(sin_prov)} sin proveedor, {len(sin_fb)} sin fallback registrado")
    di(f"     no-conformidad del modelo (ok_sin_token, NO es fallo): {len(sin_token)}")
    if can_mal:
        fallos.append(f"{len(can_mal)} canario(s) con fallo estructural")
    if sin_prov:
        fallos.append(f"{len(sin_prov)} canario(s) sin proveedor registrado")
    if sin_fb:
        fallos.append(f"{len(sin_fb)} canario(s) sin fallback registrado")
    if len(can) < len(hc) - 1:
        fallos.append(f"el canario corrió {len(can)} veces frente a {len(hc)} ciclos")

    # 6. deduplicación y recuperación coherentes
    info = [d for d in alertas if d.get("severity") == "info"]
    err = [d for d in alertas if d.get("severity") != "info"]
    di(f"6. alertas entregadas: {len(err)} de fallo, {len(info)} de recuperación, "
       f"{len(suprimidas)} suprimidas por deduplicación")
    if len(info) > len(err):
        fallos.append("hay más avisos de recuperación que de fallo: la transición no es coherente")
    if err and not suprimidas and len(err) > 1:
        fallos.append("varias alertas de fallo sin ninguna supresión: la deduplicación no actuó")

    # 7. los avisos reales respetan la cadencia documentada
    detalle, problemas = clasificar_alertas(alertas, fallidas)
    previstos = [d for d in detalle if d["clase"] == "previsto"]
    fuera = [d for d in detalle if d["clase"] in ("fuera_de_cadencia", "duplicado")]
    tope_h = BACKOFF_MAX_S / 3600
    di(f"7. cadencia de los avisos (1 h → 2 h → 4 h → … → {tope_h:.0f} h): "
       f"{len(previstos)} previsto(s), {len(fuera)} fuera de cadencia, "
       f"{len(fallidas)} sin entregar")
    for d in detalle:
        marca = {"previsto": "   ok ", "fuera_de_cadencia": "  MAL ",
                 "duplicado": "  DUP ", "no_entregado": " NOSAL"}[d["clase"]]
        extra = ""
        if "exigia_h" in d:
            extra = f"  esperó {d['transcurrido_h']} h de {d['exigia_h']} h exigidas"
        elif d.get("motivo"):
            extra = f"  ({d['motivo']})"
        di(f"   {marca} {d['ts']}  {d['monitor']} [{d['severidad']}] "
           f"reavisos={d.get('reavisos','-')}{extra}")
    fallos.extend(problemas)

    # 8. ningún aviso se quedó sin entregar
    #    Un aviso que no sale es peor que un aviso que no se emite: el registro
    #    dice que se avisó y nadie lo recibió. Es el defecto que causó UMB-276.
    di(f"8. avisos que no se pudieron entregar: {len(fallidas)}")
    for d in fallidas[:5]:
        di(f"     {d.get('ts')} {d.get('monitor')} motivo={d.get('motivo')}")
    if fallidas:
        fallos.append(f"{len(fallidas)} aviso(s) no se pudieron entregar")

    # 9. ningún aviso simulado: si aparece, producción corrió en modo de prueba
    simulados = leer(ops, desde, hasta, {"monitor_alert_simulado"})
    di(f"9. avisos simulados (modo de prueba) en la ventana: {len(simulados)}")
    if simulados:
        fallos.append(f"{len(simulados)} aviso(s) simulado(s): producción corrió en modo de prueba")

    return fallos


def autoprueba() -> int:
    """El verificador, verificado. Cada caso debe dar el veredicto esperado."""
    R = "rel-abc"
    T0 = datetime(2026, 9, 19, 14, 0, tzinfo=timezone.utc)

    def marca(minutos: int) -> str:
        return (T0 + timedelta(minutes=minutos)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def base() -> list[dict]:
        ev = []
        for i in range(48):                      # 24 h a un ciclo cada 30 min
            ev.append({"ts": marca(i * 30), "kind": "health_check",
                       "release": R, "status": "ok", "failures": 0})
            ev.append({"ts": marca(i * 30), "kind": "canary_inference",
                       "release": R, "status": "ok",
                       "provider": "anthropic", "fallback_used": True})
        return ev

    def alerta(minutos: int, n: int, sev: str = "warn", fp: str = "f1") -> dict:
        return {"ts": marca(minutos), "kind": "monitor_alert", "release": R,
                "monitor": "m", "severity": sev, "fingerprint": fp,
                "reavisos": n, "entrega": "ok"}

    def suprimida(minutos: int) -> dict:
        return {"ts": marca(minutos), "kind": "monitor_alert_suppressed",
                "monitor": "m", "severity": "warn", "fingerprint": "f1"}

    def cambiar(eventos, ts, **campos):
        return [{**e, **campos} if e["ts"] == ts else e for e in eventos]

    casos = [
        ("24 h limpias", base(), True),
        ("un ciclo omitido", [e for e in base() if e["ts"] != marca(150)], False),
        ("una alarma real",
         [{**e, "status": "fail"} if e["ts"] == marca(150) and e["kind"] == "health_check" else e
          for e in base()], False),
        ("evento de otro release", cambiar(base(), marca(180), release="otro"), False),
        ("cadencia correcta: 1 h y luego 2 h",
         base() + [alerta(0, 0), suprimida(30), alerta(60, 1), alerta(180, 2)], True),
        ("reaviso media hora despues de avisar",
         base() + [alerta(0, 0), alerta(30, 1), suprimida(10)], False),
        ("el contador de reavisos no avanza",
         base() + [alerta(0, 0), alerta(60, 0), suprimida(10)], False),
        ("aviso que no se pudo entregar",
         base() + [{"ts": marca(60), "kind": "monitor_alert_failed", "release": R,
                    "monitor": "m", "severity": "error", "fingerprint": "f1",
                    "motivo": "error_de_envio"}], False),
        ("canario sin proveedor",
         [{**e, "provider": ""} if e["kind"] == "canary_inference" and e["ts"] == marca(240) else e
          for e in base()], False),
        ("canario con fallo estructural",
         [{**e, "status": "fail"} if e["kind"] == "canary_inference" and e["ts"] == marca(240) else e
          for e in base()], False),
        ("el canario dejo de correr en la mitad de los ciclos",
         [e for i, e in enumerate(base()) if not (e["kind"] == "canary_inference" and i % 4 == 1)], False),
        ("un aviso duplicado en el mismo minuto",
         base() + [alerta(0, 0), alerta(0, 1), suprimida(10)], False),
        ("un aviso simulado colado en produccion",
         base() + [{"ts": marca(60), "kind": "monitor_alert_simulado", "release": R,
                    "monitor": "m", "severity": "warn", "fingerprint": "f1",
                    "entrega": "simulada"}], False),
        ("una recuperacion reinicia el retroceso",
         base() + [alerta(0, 0), alerta(60, 1), alerta(180, 2),
                   alerta(200, 0, sev="info", fp="rec"), alerta(210, 0), suprimida(10)], True),
    ]

    fallos_autoprueba = 0
    for nombre, eventos, debe_pasar in casos:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ops_log.jsonl"
            p.write_text("".join(json.dumps(e) + "\n" for e in eventos), encoding="utf-8")
            problemas = evaluar(p, T0.strftime("%Y-%m-%dT%H:%M:%SZ"), 24.0, R, silencioso=True)
        paso = not problemas
        ok = paso == debe_pasar
        print(f"  [{'OK  ' if ok else 'MAL '}] {nombre}: "
              f"{'pasa' if paso else 'no pasa'} (esperado: {'pasa' if debe_pasar else 'no pasa'})")
        if not ok:
            for x in problemas:
                print(f"           {x}")
            fallos_autoprueba += 1

    print()
    if fallos_autoprueba:
        print(f"AUTOPRUEBA: {fallos_autoprueba} caso(s) MAL — el verificador no es de fiar")
        return 1
    print(f"AUTOPRUEBA: {len(casos)}/{len(casos)} — el verificador distingue lo que dice distinguir")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default=None,
                    help="inicio de la ventana, UTC (por defecto: el despliegue del release activo)")
    ap.add_argument("--horas", type=float, default=24.0)
    ap.add_argument("--ops", default=os.path.expanduser("~/.config/umbral/ops_log.jsonl"))
    ap.add_argument("--archive", action="append", default=[], type=Path,
                    help="archivo rotado JSONL o .gz; repetir para fuentes fuera del directorio activo")
    ap.add_argument("--release", default=None)
    ap.add_argument("--autoprueba", action="store_true")
    a = ap.parse_args()

    if a.autoprueba:
        return autoprueba()

    active = Path(a.ops).expanduser()
    # Los archivos adyacentes se descubren por nombre; archivos guardados fuera
    # del directorio activo se declaran explícitamente, sin leer env ni secretos.
    adjacent = [p for p in active.parent.glob(active.name + ".*")
                if p.name.removeprefix(active.name + ".").removesuffix(".gz").isdigit()]
    try:
        ops = Registro(tuple([active, *adjacent, *a.archive]))
    except RegistroInvalido as exc:
        print(f"REGISTRO INCOMPLETO: {exc}")
        return 1
    print("Fuentes verificadas (snapshot de lectura):")
    for manifest in ops.manifests:
        print(json.dumps(manifest, ensure_ascii=False))
    print(f"copias de eventos eliminadas entre fuentes: {ops.duplicates}")

    release = a.release or Path(os.path.expanduser("~/.umbral/current/RELEASE_SHA")).read_text().strip()
    desde = a.desde
    if not desde:
        # La ventana empieza cuando se desplegó el release que se está juzgando, y
        # eso ya está escrito en la fuente canónica: no hace falta una superficie
        # nueva ni fiarse de lo que yo recuerde.
        desde = ultimo_despliegue(ops, release)
        if not desde:
            print(f"no hay evento release_deploy para {release[:12]} en las fuentes; "
                  "añade los archivos rotados con --archive. No se inventa un inicio.")
            return 1
        print(f"(ventana tomada del despliegue registrado en ops_log.jsonl: {desde})")

    # Una ventana a medias no se juzga. Sin esta guarda, una medición temprana
    # cuenta como "faltan ciclos" lo que en realidad es "aún no han ocurrido", y
    # eso es indistinguible de un fallo real: la misma ambigüedad que este frente
    # existe para eliminar.
    fin = momento(desde) + timedelta(hours=a.horas)
    ahora = datetime.now(timezone.utc)
    if ahora < fin:
        restan = (fin - ahora).total_seconds() / 3600
        print(f"ventana         : {desde} .. {fin.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        print(f"VENTANA INCOMPLETA: faltan {restan:.1f} h. No se emite veredicto.")
        print("(para inspeccionar el avance parcial: --horas con el tiempo ya transcurrido)")
        return 2

    fallos = evaluar(ops, desde, a.horas, release)

    print()
    if fallos:
        print("GATE 24 h: NO SUPERADO")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print("GATE 24 h: SUPERADO")
    print("  -> Solo acredita la ventana indicada; no cierra incidentes ni activa T3-C.")
    print("  -> Los incidentes posteriores y el testigo externo se evalúan por separado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
