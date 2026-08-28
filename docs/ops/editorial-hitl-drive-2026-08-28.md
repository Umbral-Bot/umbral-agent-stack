# Editorial HITL en Drive - persistencia durable

> Estado: contrato de código. No implica deploy, regeneración live ni apertura del poller.
> Fecha: 2026-08-28.

## Objetivo

Los enlaces de exportación de Magnific son temporales. En el mismo tick de
`magnific.generate_variants`, el Worker persiste las cinco alternativas PNG en
Google Drive antes de declarar la fila `Listo para selección`. Notion conserva
enlaces durables para el HITL humano y, por separado, locators oficiales de las
creaciones Magnific cuando el API realmente los entrega.

La carpeta operativa ya existe en:

```text
G:\Mi unidad\02_Operacion\Entidades Propias\Umbral BIM\04_Operacion y Alianzas\_HITL_editorial
```

Su `00_LEEME.md` existente define esta superficie como carpeta de trabajo, no
como archivo canónico, y pide cinco alternativas por fila. Este paquete no crea,
mueve ni reescribe esa carpeta o su README.

## Estructura lógica

El Worker crea sólo hijos de la raíz allowlisteada:

```text
_HITL_editorial/
└── <publication_id>/
    └── <YYYYMMDD-HHmm>/
        ├── alt-1.png
        ├── alt-2.png
        ├── alt-3.png
        ├── alt-4.png
        └── alt-5.png
```

El nombre lógico se deriva de `publication_id` y del minuto UTC de generación; no
acepta separadores ni componentes de ruta aportados por el caller.

## Configuración fail-closed

Antes de gastar créditos Magnific, el Worker comprueba la presencia de:

- `MAGNIFIC_API_KEY`
- `GOOGLE_DRIVE_EDITORIAL_HITL_FOLDER_ID`
- `GOOGLE_DRIVE_OAUTH_CLIENT_ID`
- `GOOGLE_DRIVE_OAUTH_CLIENT_SECRET`
- `GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN`

Los valores viven sólo en el entorno de runtime. `openclaw/env.template` contiene
nombres y placeholders, nunca credenciales ni IDs reales.

El OAuth puede ser el mismo que usa PIT, pero el destino no. El upload editorial
acepta exclusivamente `GOOGLE_DRIVE_EDITORIAL_HITL_FOLDER_ID` o carpetas hijas que
el propio flujo creó debajo de esa raíz. `GOOGLE_DRIVE_PIT_FOLDER_ID` no es fallback
ni destino válido para editorial; ambos envs con el mismo valor también fallan
cerrado. Un folder solicitado fuera del allowlist produce error antes de subir.

El scope se mantiene en `drive.file`; este paquete no lo ensancha a `drive`. Tras el
merge/deploy, la raíz existente debe compartirse con la cuenta OAuth de Rick como
Editor. Si el probe read-only de la raíz responde 403, el gate live queda `BLOCKED`:
no se amplía el scope como atajo y se revisa primero que la carpeta haya sido
compartida/abierta para ese cliente OAuth.

`--dry-run` no llama Magnific ni Drive. Reporta `would_persist_drive`, el path
lógico y la disponibilidad booleana de la configuración, sin imprimir valores.

## Ciclo atómico 5/5

1. Validar credenciales, root editorial allowlisteado, capacidad
   `canAddChildren` (Editor) y payload.
2. Generar y completar cinco tareas Magnific por REST.
3. Descargar cada imagen desde la URL HTTPS de exportación devuelta por el API;
   nunca descargar desde una página `app.magnific.com`. El API puede entregar
   PNG, JPEG o WebP: el Worker decodifica una imagen estática acotada y la
   normaliza a PNG antes de persistirla.
4. Crear las dos subcarpetas y subir `alt-1.png` a `alt-5.png`.
5. Obtener el `webViewLink` de la subcarpeta y de cada archivo.
6. Hacer un único patch final de Notion con el conjunto nuevo y poner
   `Estado imagen = Listo para selección`.

Se usa `webViewLink` porque las propiedades URL de Notion son puntos de acceso
humanos para revisión y deben seguir siendo válidas después de expirar el CDN.
`webContentLink` no forma parte del contrato actual: sólo se adoptaría si un
consumidor de preview directo lo exige y se documenta con una prueba específica.

Si Magnific no completa 5/5 o Drive falla al crear, descargar o subir, el Worker:

- no pone `Listo para selección`;
- escribe `Estado imagen = Error` y un diagnóstico redactado;
- conserva el conjunto anterior de `HITL Drive`, `imagen_alt_*_url`, cantidad y
  fecha hasta que exista un reemplazo completo 5/5;
- conserva el marcador de intento para que el poller no vuelva a gastar créditos
  Magnific en cada ciclo.

Una subida parcial puede dejar objetos no referenciados en Drive. Su limpieza es
una operación separada y destructiva; este flujo no los borra automáticamente.

## Contrato de columnas Publicaciones

| Propiedad | Contenido | Productor / consumidor |
|---|---|---|
| `HITL Drive` | `webViewLink` de la subcarpeta de la generación completa | Worker / David |
| `imagen_alt_N_url` | `webViewLink` durable de `alt-N.png` | Worker / selector HITL |
| `imagen_alt_N_magnific_url` | Locator HTTPS oficial entregado por Magnific, si existe | Worker / trazabilidad |
| `Visual asset URL` | Copia de `imagen_alt_N_url` después de elegir `Alt N` | Selector / publish |

El Worker nunca construye un permalink Magnific a partir de `task_id`, identifier
o una plantilla de URL. Si el payload completado no aporta un locator oficial, la
propiedad `imagen_alt_N_magnific_url` queda vacía. Los identificadores técnicos se
conservan en memoria durante la ejecución para validar que cada respuesta corresponde
a la tarea consultada; no se publican como URLs ni se convierten en errores falsos.

`Visual asset URL` apunta a la candidata durable seleccionada durante este tramo
pre-T18. Esto no contradice `00_LEEME.md`: no se deposita un archivo de overlay
final dentro de `_HITL_editorial`. La aplicación de la plantilla T18 y el destino
del asset final pertenecen a una fase posterior y están fuera de este paquete.

## Regeneración y pruebas

Al pedir `Regenerar`, las URLs previas siguen visibles hasta completar otra
generación y persistencia Drive 5/5. Sólo entonces se reemplaza el conjunto en un
patch final.

Las pruebas de este paquete usan mocks/fakes de HTTP, Drive y Notion. No generan
la fila HITL, no escriben en Drive live, no despliegan en VPS y no habilitan el
poller Magnific.

## Referencias

- `docs/ops/notion-publicaciones-v2-visual-gates-schema.md`
- `docs/ops/editorial-magnific-p22-poller-2026-07-23.md`
- `docs/ops/pit-telegram-drive-deliverables-runbook.md`
- `notion/schemas/publicaciones.schema.yaml`
- `scripts/editorial/sync_visual_asset_from_selection.py`
