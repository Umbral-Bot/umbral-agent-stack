# Spike 013-K — VM + YouTube Data API

- Started: `2026-05-07T14:39:58.279159+00:00`
- Finished: `2026-05-07T14:40:07.148559+00:00`
- Source sample (013-J ids): `reports/spike-youtube-20260507T055904Z.json`
- Sample size: 8
- VM health: ok=True version=0.4.0 has_browser_navigate=True has_yt_dlp_task=False
- Data API key present: True

## Comparison

| alt | sample_size | success% | has_transcript | has_long_desc | avg_latency_ms | blockers |
| --- | --- | --- | --- | --- | --- | --- |
| VIA A — VM browser (residential IP probe) | 8 | 0% | n/a (probe-only) | n/a (probe-only) | 858.1 | VM IP también bloqueado por Google: 8/8 requests redirigidos a `google.com/sorry/index?...` (reCAPTCHA). El supuesto 'IP residencial de la VM destraba YouTube' NO se cumple con esta VM. Owner: Rick — evaluar proxy residencial pago, cookies de browser real, o descartar VIA A definitivamente. Mientras tanto, VIA A NO es una solución para 013-K.; VM worker no tiene tarea `youtube.fetch` registrada — esto es la implementación esperada de 013-K (no es bloqueo del spike, es el work-item resultante). |
| VIA B — YouTube Data API v3 | 8 | 88% | NO (Data API does not expose transcripts) | 88% | 249.9 | — |

## Blockers

**VIA A:**
- VM IP también bloqueado por Google: 8/8 requests redirigidos a `google.com/sorry/index?...` (reCAPTCHA). El supuesto 'IP residencial de la VM destraba YouTube' NO se cumple con esta VM. Owner: Rick — evaluar proxy residencial pago, cookies de browser real, o descartar VIA A definitivamente. Mientras tanto, VIA A NO es una solución para 013-K.
- VM worker no tiene tarea `youtube.fetch` registrada — esto es la implementación esperada de 013-K (no es bloqueo del spike, es el work-item resultante).

**VIA B:** ninguno detectado.

## Useful fields by source

- VIA A (residential-IP signal via `browser.navigate`): presence of `ytInitialPlayerResponse`, absence of bot wall. NOT a full extraction; confirms that adding a `youtube.fetch` task on the VM (yt-dlp + youtube-transcript-api) would have access to the real player + transcripts.
- VIA B (Data API `videos?part=snippet,contentDetails,statistics`): title, description, tags, channelId, channelTitle, publishedAt, duration (ISO 8601 → seconds), viewCount, likeCount, commentCount, defaultLanguage, defaultAudioLanguage, categoryId. Does **not** include captions/transcript (separate Captions API endpoint with different scopes).

## Recommendation

RECOMENDACIÓN 013-K: implementar SOLO VIA B (YouTube Data API v3). VIA A invalidada: 100% de requests desde la VM son redirigidos a `google.com/sorry` (reCAPTCHA) — el IP de la VM también está flagged por Google. Data API entrega 88% de descripciones >500c, suficiente para evitar created_no_body. Sin transcript: aceptable para Stage 2 v1.

## Per-video results

| sqlite_id | video_id | VIA A useful | VIA A bot_wall | VIA B ok | VIA B desc_len | VIA B duration_s |
| --- | --- | --- | --- | --- | --- | --- |
| 52 | `Vht4hoRHEek` | False | True | True | 1835 | 3896 |
| 81 | `9Gr2QjvSQ-I` | False | True | True | 886 | 1851 |
| 82 | `3LnNwS6rqk8` | False | True | True | 1723 | 1478 |
| 111 | `s2jm2Z22ibA` | False | True | True | 4863 | 2368 |
| 141 | `TQsBnsKZtuo` | False | True | True | 1428 | 812 |
| 142 | `npmoS_dqAho` | False | True | True | 1456 | 1410 |
| 261 | `J26M-cpFG-M` | False | True | True | 1045 | 103 |
| 262 | `FNfIMnpz-ZY` | False | True | False | - | - |
