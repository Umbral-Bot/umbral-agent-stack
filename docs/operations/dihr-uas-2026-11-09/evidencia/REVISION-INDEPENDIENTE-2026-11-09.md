<!-- Informe íntegro del subagente revisor (instrucción: refutar; solo archivos locales). Sesión coordinadora local_815b91f1, 2026-11-09 ~06:55Z. Las correcciones aplicadas se anotan al final. -->

# Revisión independiente — DIHR UAS corte 2026-11-09

Alcance: solo archivos locales listados. Comprobaciones propias: SHA-256 del acta = `85c9e86f…346` (coincide); clone `-claude` en `main`, HEAD `57879ae` 2026-09-05, 0/16 detrás (coincide con inventario TARRO §8); barrido de patrones de secretos en la carpeta (sin tokens ni claves).

## 1. Tabla de hallazgos

| ID | Sev. | Ubicación | Afirmación | Por qué falla | Corrección |
|---|---|---|---|---|---|
| H1 | Alta | Doc A.1-10a, D10, D.17 | 100 k `poll_comments`/7 d «consumen la cuota de 180 req/min» y «explican los 429/HTML» | 100.051/604.800 s ≈ 10 req/min = 5,5 % de 180. Ningún «429» en la evidencia; poller 0 fallos/24 h; 5 HTML sobre 100 k. Motivo de D10 no sostenido. | Reformular D10 como optimización de carga; medir req/min reales antes de tocar el intervalo. |
| H2 | Alta | D1; VPS-01 §1; VPS-02 | `--max-old-space-size=3072`, `MemoryHigh=5G`, `MemoryMax=6G` | RAM 7,94 GB, disponible 997→618 MB; RSS 4,43 GB con heap 2,2 GB ⇒ ~2–3 GB externos. cgroup ya en 5,45 GB > MemoryHigh=5G. Heap 3 GB + externos ≈ 6+ GB ⇒ MemoryMax mata antes del snapshot; snapshot exige RAM extra con <1 GB libre; `RestartMaxDelaySec=120` alarga cortes. | Declarar riesgo; secuenciar compactar sesión y sacar canario antes de subir heap; MemoryMax ≥ 6,5 G y MemoryHigh ≥ uso actual; verificar RAM libre para snapshot. |
| H3 | Alta | C, J, ledger | Digest Notion como evidencia | `evidencia/notion-uas-digest.md` tenía solo la cabecera. | Adjuntar el digest real o degradar a «Reportado». |
| H4 | Alta | COMPARATIVA-01, RELEVO, Doc B.5, TARRO, Drive | — | Expone ID del archivo de correspondencia de códigos del juez, URL del GDoc de control privado, IP pública + usuario SSH del VPS, email personal y handle gmail de un tercero. | Truncar/redactar antes de commit/PR. |
| H5 | Media | A.1-2, A.1-6, A.1-9, H; PCRick-01 «Cruce» | Presentado como «verificado» | (i) causa del bloqueo de Rick GPT es nota del coordinador; (ii) ensayo docente y hash b7aefd23 son relevo; (iii) caducidad de TARRO solo vista desde PCRick; (iv) «Connection refused = OOM»: una coincidencia; 10 refused vs 7 restarts; el Cruce atribuye al VPS 7 refused que VPS-01 no reporta. | Etiquetar como Hipótesis/Reportado; corregir el Cruce. |
| H6 | Media | A.1-4, B.1, B.5 | Worker PCRick «0 peticiones externas desde 14-oct» | PCRick-01 no da fecha; B.5 dice que la ruta requería Tailscale caída desde 25-ago: contradicción. | Citar fuente de la fecha; aclarar ruta. |
| H7 | Media | D.13, R2.3 | «2 checkpoints Hyper-V de febrero» | PCRick-01 §8: NO PROBADO; TARRO sin elevación. | Marcar no verificado; R2.3 condicionado. |
| H8 | Media | D3 | «GOOGLE_API_KEY ya está en el proceso» | VPS-01 solo dice «sin OPENAI_API_KEY»; ruta de config difiere entre doc e investigación. | Verificar env y clave de config antes de D3. |
| H9 | Media | A.1-10c, D9 | «nada indica que se revirtiera»; reversión «desde sus .bak» | PCRick-01 registra settings.local.json modificado 09-11 03:59Z; los .bak no constan. | Leer los 3 archivos; crear .bak como paso 0. |
| H10 | Media | ledger, D.8, A.1-6, H | «ACK < 1 min, REPORT 3–8 min», «cuatro paquetes» | ts de ACK idénticos a EMITIDO (escritura diferida); A.1-6 dice 4, H dice 6. | Declarar ts de escritura; unificar conteo. |
| H11 | Media | F, G | Hoja de ruta | «sin gasto nuevo» vs restic externo, runner headless, Langfuse; G11 imposible con runner en PCRick (VM de TARRO); R1.3 E2E no depende de D4 (ruta por nodo existe); E1.3 choca con «no eludir ni desactivar» el monitor; E2 criterio depende de middleware no existente; «notion-governance» como responsable es un repo. | Costos por paquete; G11 solo con runner en VPS; E2E hoy por nodo; E1.3 decisión de David; E2 criterio verificable. |
| H12 | Media | K | «pesos fijados antes de puntuar» | No constan en ESTADO.md ni ledger. | Registrar pesos en ledger con ts. |
| H13 | Baja | varios | Números | llm_usage por proveedor suma 124 ≠ 158; «.env con 26 claves» (son 21 entradas); «8–9 h» inferencia; «22 chat.abort/52 entradas» e «índice PCRick 0 fuentes» citan sesiones no incluidas en evidencia/; cifras Azure, créditos Anthropic diferidos, Power Automate solo en C28, contraseña 11-sep sin fuente en el paquete. | Añadir fuente o marcar Reportado. |
| H14 | Baja | A.2, I, K | «D1–D8» | La tabla tiene D1–D10 con D9/D10 antes de D8. | Renumerar; actualizar I y K. |
| H15 | Baja | D7, D.13, A.1-5, A.1-9, H | Omisiones | PCRick expone Worker 0.0.0.0:8088, sshd 22 y SMB 445/139; credencial Grok Bot y `env.rick-oauth.pending` con refresh tokens fuera de D7; `pit-judge-open.ps1` con túnel SSH existe (MC alcanzable por script); PBIX modificado 4 min después del PASS_PARTIAL; sesión COMPARATIVA creó 15 archivos + 1 carpeta en Drive hoy; «88 archivos leída» → solo 2 abiertos. | Incorporar. |

## 2. Bien soportado (conservar)
Causas (a)(b)(c) de la degradación de Rick con comando, hora y cifras; tailnet caída (NeedsLogin + Expired visto desde PCRick); nodo único confirmado desde ambos lados; Mission Control en loopback 8089 y aclaración de prototipos; hash del acta y estado del clone verificados; inventario TARRO con comando por ítem; comparativa fiel a JUEZ/COMPARATIVA con PASS_PARTIAL como inferencia; D.16/D.17 fieles a VPS-02; D2, D4, D5 proporcionadas y reversibles; leyenda Verificado/Reportado/Hipótesis; sección H; investigación con fuentes primarias.

## 3. Puntuación alternativa de K (revisor, antes de correcciones)
Inventario 65 → 9,75 · Diagnóstico 60 → 15,0 · Investigación 75 → 7,5 · Entrevista 85 → 8,5 · Propuestas 55 → 8,25 · Hoja de ruta 45 → 6,75 · Revisión 50 → 5,0 · **Total ≈ 61 %** (56 % sin la revisión).

## 4. Veredicto
**APTO_CON_CORRECCIONES.** Mínimas para APTO: H1, H2, H3, H4, H5, H7, H11, H14.

---
## Correcciones aplicadas por el coordinador (2026-11-09 ~07:00Z)
H1 D10 reformulada (optimización, sin «cuota/429»). H2 D1 re-dimensionada y secuenciada con riesgo declarado. H3 digest escrito íntegro (se completó tras la lectura del revisor). H4 redactados ID de correspondencia, URL del GDoc de control, usuario@IP del VPS, email y handle de tercero en documento y evidencia. H5 reetiquetado como Reportado/Hipótesis; Cruce corregido. H6 fuente de la fecha añadida (tabla PCRick 08-nov leída en pestaña) y ruta aclarada. H7 checkpoints → según ficha 006 (12-sep), hoy no verificado. H8 fuente (sesión VPS 00:51Z) y verificación previa añadidas a D3. H9 paso 0 de lectura y .bak en D9. H10 nota sobre ts de escritura y conteo unificado (6 paquetes). H11 costos por paquete, G11 con runner en VPS, E2E por nodo sin esperar D4, E1.3 como decisión de David, E2 criterio verificable, responsable «escritor de notion-governance (Codex)». H12 pesos registrados en ledger. H13 cifras corregidas o marcadas Reportado con fuente. H14 renumeradas D1–D10 en orden. H15 incorporadas omisiones. K recalculado.
