# Spike 013-K — VM + YouTube Data API

- Started: `2026-05-07T13:44:30.460162+00:00`
- Finished: `2026-05-07T13:44:36.481206+00:00`
- Source sample (013-J ids): `reports/spike-youtube-20260507T055904Z.json`
- Sample size: 8
- VM health: ok=True version=0.4.0 has_browser_navigate=True has_yt_dlp_task=False
- Data API key present: False

## Comparison

| alt | sample_size | success% | has_transcript | has_long_desc | avg_latency_ms | blockers |
| --- | --- | --- | --- | --- | --- | --- |
| VIA A — VM browser (residential IP probe) | 8 | 0% | n/a (probe-only) | n/a (probe-only) | 752.1 | VM IP también bloqueado por Google: 8/8 requests redirigidos a `google.com/sorry/index?...` (reCAPTCHA). El supuesto 'IP residencial de la VM destraba YouTube' NO se cumple con esta VM. Owner: Rick — evaluar proxy residencial pago, cookies de browser real, o descartar VIA A definitivamente. Mientras tanto, VIA A NO es una solución para 013-K.; VM worker no tiene tarea `youtube.fetch` registrada — esto es la implementación esperada de 013-K (no es bloqueo del spike, es el work-item resultante). |
| VIA B — YouTube Data API v3 | 8 | 0% | NO (Data API does not expose transcripts) | 0% | None | YOUTUBE_DATA_API_KEY no presente. Owner: David — crear API key en Google Cloud Console (proyecto nuevo o existente), habilitar 'YouTube Data API v3', restringir por IP de la VPS, y exportar la variable en el systemd unit del dispatcher. |

## Blockers

**VIA A:**
- VM IP también bloqueado por Google: 8/8 requests redirigidos a `google.com/sorry/index?...` (reCAPTCHA). El supuesto 'IP residencial de la VM destraba YouTube' NO se cumple con esta VM. Owner: Rick — evaluar proxy residencial pago, cookies de browser real, o descartar VIA A definitivamente. Mientras tanto, VIA A NO es una solución para 013-K.
- VM worker no tiene tarea `youtube.fetch` registrada — esto es la implementación esperada de 013-K (no es bloqueo del spike, es el work-item resultante).

**VIA B:**
- YOUTUBE_DATA_API_KEY no presente. Owner: David — crear API key en Google Cloud Console (proyecto nuevo o existente), habilitar 'YouTube Data API v3', restringir por IP de la VPS, y exportar la variable en el systemd unit del dispatcher.

## Useful fields by source

- VIA A (residential-IP signal via `browser.navigate`): presence of `ytInitialPlayerResponse`, absence of bot wall. NOT a full extraction; confirms that adding a `youtube.fetch` task on the VM (yt-dlp + youtube-transcript-api) would have access to the real player + transcripts.
- VIA B (Data API `videos?part=snippet,contentDetails,statistics`): title, description, tags, channelId, channelTitle, publishedAt, duration (ISO 8601 → seconds), viewCount, likeCount, commentCount, defaultLanguage, defaultAudioLanguage, categoryId. Does **not** include captions/transcript (separate Captions API endpoint with different scopes).

## Recommendation

RECOMENDACIÓN 013-K: VIA A INVALIDADA. La VM está reachable y `browser.navigate` funciona, pero 100% de los requests son redirigidos a `google.com/sorry/index?...` con un reCAPTCHA — el IP de egreso de la VM también está marcado por Google. Conclusión: cambiar de IP residencial NO es la solución; el problema es 'cualquier IP que ya pegó suficientes requests a YouTube'. **Próximo paso obligatorio:** desbloquear VIA B (YouTube Data API v3). David debe crear la API key — sin eso, Stage 2 para canal=youtube queda en stub. NO implementar yt-dlp en la VM hasta resolver el captcha del lado VM (cookies de un browser real, rotación de IP, o proxy residencial pago).

## Per-video results

| sqlite_id | video_id | VIA A useful | VIA A bot_wall | VIA B ok | VIA B desc_len | VIA B duration_s |
| --- | --- | --- | --- | --- | --- | --- |
| 52 | `Vht4hoRHEek` | False | True | False | - | - |
| 81 | `9Gr2QjvSQ-I` | False | True | False | - | - |
| 82 | `3LnNwS6rqk8` | False | True | False | - | - |
| 111 | `s2jm2Z22ibA` | False | True | False | - | - |
| 141 | `TQsBnsKZtuo` | False | True | False | - | - |
| 142 | `npmoS_dqAho` | False | True | False | - | - |
| 261 | `J26M-cpFG-M` | False | True | False | - | - |
| 262 | `FNfIMnpz-ZY` | False | True | False | - | - |
