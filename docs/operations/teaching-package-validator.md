# Verificador de paquetes docentes

`scripts/validate_teaching_package.py` — utilidad offline, de solo lectura y sin
dependencias externas (solo biblioteca estándar, Python ≥ 3.10) que valida un
paquete docente contra un manifiesto CSV.

Origen: piloto `PKG-UAS-CLOUD-PILOT-01-20260929`
(`.agents/tasks/2026-09-29-001-cloud-docente-pilot.md`).

## Uso

```bash
python scripts/validate_teaching_package.py RAIZ --manifest MANIFIESTO.csv \
    --role {teacher,student} \
    [--forbid RUTA ...] [--forbidden-list ARCHIVO] [--reviewed-ok RUTA ...] \
    [--json-out ARCHIVO_FUERA_DE_RAIZ]
```

- Sin `--json-out`: JSON a stdout, resumen legible a stderr.
- Con `--json-out`: JSON al archivo, resumen a stdout. El destino debe estar
  **fuera** de la raíz (el informe no altera el inventario) y **no debe existir**:
  política *exclusive-create* (`O_CREAT|O_EXCL`). Un archivo existente, sea
  normal, symlink o hardlink de un insumo (dentro o fuera de la raíz: material,
  manifiesto, lista de prohibidos), se rechaza con exit 2 sin tocarlo.

| Exit | Significado |
|------|-------------|
| 0 | `PASS`: paquete íntegro |
| 1 | `FAIL`: hay hallazgos |
| 2 | Invocación/configuración inválida (raíz inexistente, manifiesto ilegible, no UTF-8, sin columnas requeridas, `--json-out` dentro de la raíz, opciones de alumno con `--role teacher`, argumentos inválidos) |

## Manifiesto

CSV UTF-8 (con o sin BOM), con encabezado que contenga `ruta,bytes,sha256`
(sin distinguir mayúsculas; espacios alrededor tolerados; columnas extra
ignoradas). Soporta quoting estándar (comas y espacios dentro de rutas).

- `ruta`: relativa a la raíz; separador `/` o `\`. Se recortan espacios
  iniciales/finales; se colapsan `//` y `./`.
- `bytes`: entero no negativo.
- `sha256`: 64 hex (mayúsculas o minúsculas), calculado sobre los **bytes
  reales** del archivo, leído por streaming (1 MiB).

No sustituye a `scripts/maintenance/check_skill_mirrors.py`, que compara hashes
de texto normalizado (CRLF/LF), no bytes de materiales.

## Hallazgos (`code`)

| Código | Regla |
|--------|-------|
| `malformed_row` | Número de campos distinto al encabezado o error de quoting CSV (el parseo se detiene tras un error de quoting). |
| `path_rejected` | Ruta absoluta POSIX (`absolute_posix`), unidad Windows (`absolute_windows_drive`), UNC (`absolute_unc`), `..` (`parent_traversal`), vacía o con NUL. Se rechaza **antes** de tocar el sistema de archivos. |
| `invalid_size` | `negative` o `not_a_non_negative_integer`. |
| `invalid_hash` | No son 64 caracteres hex. |
| `duplicate_path` | Misma ruta normalizada declarada dos veces (p. ej. `a.txt` y `.\a.txt`). |
| `case_collision` | Rutas que solo difieren en mayúsculas (colisionan en Windows/Drive). |
| `missing_file` | No existe (o un componente padre no es carpeta). |
| `not_regular_file` | Es carpeta o archivo especial; no se abre. |
| `size_mismatch` / `hash_mismatch` | Tamaño o SHA-256 distintos (se informan valores esperado/real, nunca contenido). |
| `unreadable_file` | Error de permisos/E/S. |
| `inventory_incomplete` | No se pudo listar una carpeta o hacer `stat` de una entrada (p. ej. `PermissionError`). La enumeración incompleta **falla**: no se acredita inventario completo. |
| `extra_file` | Archivo en disco no declarado. Solo se excluye el propio manifiesto si está dentro de la raíz; no se excluyen docs, ocultos ni carpetas. |
| `symlink_not_allowed` | Ver política de enlaces. |
| `student_forbidden_explicit` | (alumno) Ruta o carpeta en `--forbid`/`--forbidden-list`. |
| `student_forbidden_convention` | (alumno) Nombre docente por convención. |
| `student_ambiguous_name` | (alumno) Nombre ambiguo; requiere revisión humana. |

Las filas con tamaño/hash inválido cuentan como declaradas (no generan
`extra_file`), pero no se verifican. Una fila malformada no declara nada, por lo
que su archivo aparecerá además como `extra_file`.

### Política de enlaces simbólicos

**Ninguna redirección se sigue, se lee ni se recorre**, sea interna o externa:
symlinks POSIX/Windows y *junctions*/mount points de Windows (reparse points
con el bit *name-surrogate* `0x20000000`) producen `symlink_not_allowed` con
`rule` = `symlink_internal` o `symlink_escape` (clasificado resolviendo la ruta,
sin abrir el destino). Se comprueba en cada componente de la ruta declarada y
durante el inventario. Motivo: ZIP/Drive no preservan enlaces, así que el
paquete entregado diferiría del verificado.

Reparse points que **no** son name-surrogate (placeholders de Drive/OneDrive
`IO_REPARSE_TAG_CLOUD_*`, dedup) son datos regulares y se verifican normalmente.
Defensa adicional: antes de leer, la ruta resuelta (`realpath`) debe seguir
dentro de la raíz; si no, `rule=redirect_escape` y no se lee. La apertura final
usa `O_NOFOLLOW` cuando el SO lo ofrece. Compatible con Python ≥ 3.11 (no usa
`os.path.isjunction`).

### Modo alumno (`--role student`)

Se revisan todas las rutas declaradas **y** las presentes en disco. Detección
por **nombres**, no semántica: no garantiza encontrar toda solución.

1. Lista explícita (`--forbid`, `--forbidden-list` con una ruta por línea y `#`
   para comentarios): coincidencia exacta o como carpeta prefijo. Nunca se
   anula con `--reviewed-ok`.
2. Convención fuerte: algún token de un componente (separado por no
   alfanuméricos y camelCase; sin tildes ni mayúsculas) **empieza por**
   `docente`, `teacher`, `solucion`, `solution`, `profesor` o `instructor`
   (cubre `Docentes/`, `Solucionario`, `GuiaTeacher`, `Solución`).
3. Ambiguo (fail-closed): token exacto `clave(s)`, `pauta(s)`, `key(s)`,
   `answer(s)`, `respuesta(s)`, o término fuerte dentro de un token sin estar
   al inicio. Se informa como `student_ambiguous_name` con "human review
   required"; un humano puede aceptarlo con `--reviewed-ok RUTA`, que queda
   registrado en `reviewed_overrides`.

En modo `teacher` no hay reglas de fuga.

## Salida JSON

```json
{
  "tool": "validate_teaching_package", "report_version": 1,
  "status": "PASS|FAIL", "role": "student", "root": "...", "manifest": "...",
  "counts": {"manifest_rows": 3, "valid_rows": 3, "files_hashed": 3,
             "files_on_disk": 3, "findings": 0, "by_code": {}},
  "findings": [{"code": "...", "severity": "error", "path": "...", "line": 2,
                "rule": "...", "detail": "..."}],
  "reviewed_overrides": [],
  "native_gui": "NOT_RUN", "student_download": "NOT_RUN",
  "scope": "byte integrity only; ..."
}
```

## Límites (qué NO acredita)

- `native_gui=NOT_RUN`: no abre Power BI, Revit ni otras apps.
- `student_download=NOT_RUN`: no prueba acceso/descarga del alumno ni
  sincronización con Drive.
- No modifica originales, no extrae ZIP, no ejecuta scripts del paquete, no
  imprime contenido. No accede a red, Drive, Notion ni credenciales.
- Rutas en disco con `\` literal en el nombre (Linux) no son representables en
  el manifiesto (se interpretan como separador).
- Existe una ventana TOCTOU entre la comprobación y la lectura; mitigada con
  `O_NOFOLLOW`, no eliminada. Ejecutar sobre copias en reposo.

## Ejemplo (fixtures sintéticos)

```text
$ python scripts/validate_teaching_package.py tests/fixtures/teaching_package/sano \
    --manifest tests/fixtures/teaching_package/sano.csv --role student --json-out /tmp/sano.json
Teaching package: PASS  (role=student)
rows=3 valid=3 hashed=3 on_disk=3 findings=0
native_gui=NOT_RUN student_download=NOT_RUN (integrity only)
exit=0
```

Copia defectuosa (un archivo borrado, uno con un byte añadido, `docente/pauta.txt`
extra y un symlink a `/etc/hostname`):

```text
Teaching package: FAIL  (role=student)
rows=3 valid=3 hashed=2 on_disk=3 findings=6
native_gui=NOT_RUN student_download=NOT_RUN (integrity only)
- [missing_file] Guia 01.txt (line 2)
- [size_mismatch] enunciado.md (line 4): expected 36, actual 37
- [hash_mismatch] enunciado.md (line 4): expected e5aed56d…748c, actual cedc2566…fc8c
- [extra_file] docente/pauta.txt: not in manifest
- [symlink_not_allowed] fuera.txt: symlink_escape undeclared; not followed
- [student_forbidden_convention] docente/pauta.txt: token 'docente' starts with 'docente' teacher-only naming convention
exit=1
```

## Fixtures y fin de línea

`tests/fixtures/teaching_package/.gitattributes` fija `* -text` solo para esos
fixtures sintéticos, para que `core.autocrlf=true` no convierta LF→CRLF y
cambie tamaño/SHA. El validador **no** normaliza fin de línea: hashea bytes.
Un clon previo necesita re-checkout de esos archivos para aplicar el atributo.

## Pruebas

```bash
python -m pytest tests/test_validate_teaching_package.py -q
```
