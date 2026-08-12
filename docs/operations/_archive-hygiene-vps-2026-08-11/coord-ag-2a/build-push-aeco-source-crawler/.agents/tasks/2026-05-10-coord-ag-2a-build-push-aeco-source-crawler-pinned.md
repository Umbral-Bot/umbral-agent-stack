---
id: "2026-05-10-coord-ag-2a"
title: "Coord Ag 2A - VPS - build + push aeco-source-crawler pinned (O16.2)"
status: done-vps-side
assigned_to: copilot-vps
created_by: copilot-chat-coordinator
priority: high
sprint: Q2-2026 / O16.2
created_at: "2026-05-10T09:21:38Z"
updated_at: "2026-05-10T09:21:38Z"
do_not_merge: true
---

## Contexto

Coord Ag 2 - Opción C - parte VPS. Build + push del tag pinned para
trazabilidad O16.2. Sigue el patrón de la task 052 (2026-05-08), sin
retaguear `:latest` ni `:v1` y sin tocar las otras 2 imágenes.

Coord Ag 2B (update ACA Job) lo ejecuta David desde Windows tras revisar
este reporte.

## Reporte

```
COORD AG 2A - VPS - REPORT
HEAD: 2e66ddae8fb3731fed51a2e5475dd71e9da3285c
TAG_BUILT: o16.2-2e66dda
LOCAL_DIGEST: sha256:ce04d7f5d8a96a82c9a7197394c86e60146350e21408b4eed03f868c2cbfeedc
REMOTE_DIGEST: sha256:ce04d7f5d8a96a82c9a7197394c86e60146350e21408b4eed03f868c2cbfeedc
GH_API_TAG_VISIBLE: yes
LATEST_TOCADO: NO
V1_TOCADO: NO
AZURE_TOCADO: NO
NOTION_TOCADO: NO
N8N_TOCADO: NO
RRSS_TOCADO: NO
RUNTIME_VPS_TOCADO: NO
VEREDICTO: PASS
```

## Evidencia raw

```
    === Coord Ag 2A - 2026-05-10T09:10:03Z ===
    HEAD=2e66ddae8fb3731fed51a2e5475dd71e9da3285c
    SHA7=2e66dda
    TAG=o16.2-2e66dda
    IMG=ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda
    Login Succeeded
    --- BUILD ---
    #9 4.431 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
    #9 DONE 4.6s
    
    #10 [4/8] COPY scripts/aeco-kb/__init__.py /app/scripts/aeco_kb/__init__.py
    #10 DONE 0.1s
    
    #11 [5/8] COPY scripts/aeco-kb/source_crawler.py /app/scripts/aeco_kb/source_crawler.py
    #11 DONE 0.0s
    
    #12 [6/8] COPY scripts/aeco-kb/seeds/ /app/scripts/aeco_kb/seeds/
    #12 DONE 0.0s
    
    #13 [7/8] COPY infra/docker/aeco-source-crawler/entrypoint.sh /app/entrypoint.sh
    #13 DONE 0.1s
    
    #14 [8/8] RUN chmod +x /app/entrypoint.sh && chmod -R a+r /app
    #14 DONE 0.2s
    
    #15 exporting to image
    #15 exporting layers
    #15 exporting layers 1.4s done
    #15 exporting manifest sha256:04583f14a632935242fb92ee713d86fcecec698afbb2b9fd29f19b08a455d0a6 0.0s done
    #15 exporting config sha256:2ff17c0990dc60bcc8af04b75872d1c15b5203f6a480e4533c8378911276a3c5 0.0s done
    #15 exporting attestation manifest sha256:bb044c37fbb3820f5764f001641b1731af27b07678be6ff0f49388b08b33373b 0.0s done
    #15 exporting manifest list sha256:ce04d7f5d8a96a82c9a7197394c86e60146350e21408b4eed03f868c2cbfeedc 0.0s done
    #15 naming to ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda
    #15 naming to ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda done
    #15 unpacking to ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda
    #15 unpacking to ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda 0.5s done
    #15 DONE 2.1s
    LOCAL_DIGEST=sha256:ce04d7f5d8a96a82c9a7197394c86e60146350e21408b4eed03f868c2cbfeedc
    --- PUSH ---
    The push refers to repository [ghcr.io/umbral-bot/aeco-source-crawler]
    23ca07726edd: Waiting
    bd7c572d536d: Waiting
    b7371706e36c: Waiting
    5a17feda9bf6: Waiting
    759e0c85a86e: Waiting
    b33ff618953d: Waiting
    c66009f3c914: Waiting
    4d45950cad7b: Waiting
    4ac8a6d600d7: Waiting
    a3774064c1d0: Waiting
    57fb71246055: Waiting
    797809503061: Waiting
    c66009f3c914: Waiting
    4d45950cad7b: Waiting
    4ac8a6d600d7: Waiting
    a3774064c1d0: Waiting
    57fb71246055: Waiting
    797809503061: Waiting
    23ca07726edd: Waiting
    bd7c572d536d: Waiting
    b7371706e36c: Waiting
    5a17feda9bf6: Waiting
    759e0c85a86e: Waiting
    b33ff618953d: Waiting
    759e0c85a86e: Waiting
    b33ff618953d: Waiting
    c66009f3c914: Waiting
    4d45950cad7b: Waiting
    4ac8a6d600d7: Waiting
    a3774064c1d0: Waiting
    57fb71246055: Waiting
    797809503061: Waiting
    23ca07726edd: Waiting
    bd7c572d536d: Waiting
    b7371706e36c: Waiting
    5a17feda9bf6: Waiting
    4ac8a6d600d7: Waiting
    a3774064c1d0: Waiting
    57fb71246055: Waiting
    797809503061: Waiting
    23ca07726edd: Waiting
    bd7c572d536d: Waiting
    b7371706e36c: Waiting
    5a17feda9bf6: Waiting
    759e0c85a86e: Waiting
    b33ff618953d: Waiting
    c66009f3c914: Waiting
    4d45950cad7b: Waiting
    4ac8a6d600d7: Waiting
    a3774064c1d0: Waiting
    57fb71246055: Waiting
    797809503061: Waiting
    23ca07726edd: Waiting
    bd7c572d536d: Waiting
    b7371706e36c: Waiting
    5a17feda9bf6: Waiting
    759e0c85a86e: Waiting
    b33ff618953d: Waiting
    c66009f3c914: Waiting
    4d45950cad7b: Waiting
    bd7c572d536d: Waiting
    b7371706e36c: Waiting
    5a17feda9bf6: Waiting
    759e0c85a86e: Waiting
    b33ff618953d: Waiting
    c66009f3c914: Waiting
    4d45950cad7b: Waiting
    4ac8a6d600d7: Waiting
    a3774064c1d0: Waiting
    57fb71246055: Waiting
    797809503061: Waiting
    23ca07726edd: Waiting
    797809503061: Waiting
    23ca07726edd: Waiting
    bd7c572d536d: Waiting
    b7371706e36c: Waiting
    5a17feda9bf6: Waiting
    759e0c85a86e: Waiting
    b33ff618953d: Waiting
    c66009f3c914: Waiting
    4d45950cad7b: Waiting
    4ac8a6d600d7: Waiting
    a3774064c1d0: Waiting
    57fb71246055: Waiting
    4ac8a6d600d7: Waiting
    a3774064c1d0: Waiting
    57fb71246055: Waiting
    797809503061: Waiting
    23ca07726edd: Waiting
    bd7c572d536d: Waiting
    b7371706e36c: Waiting
    5a17feda9bf6: Waiting
    759e0c85a86e: Waiting
    b33ff618953d: Waiting
    c66009f3c914: Waiting
    4d45950cad7b: Waiting
    b33ff618953d: Waiting
    c66009f3c914: Waiting
    4d45950cad7b: Waiting
    4ac8a6d600d7: Waiting
    a3774064c1d0: Waiting
    57fb71246055: Waiting
    797809503061: Waiting
    23ca07726edd: Waiting
    bd7c572d536d: Waiting
    b7371706e36c: Waiting
    5a17feda9bf6: Waiting
    b33ff618953d: Pushed
    c66009f3c914: Pushed
    4ac8a6d600d7: Pushed
    a3774064c1d0: Pushed
    23ca07726edd: Pushed
    bd7c572d536d: Pushed
    b7371706e36c: Pushed
    4d45950cad7b: Pushed
    797809503061: Pushed
    759e0c85a86e: Pushed
    5a17feda9bf6: Pushed
    57fb71246055: Pushed
    o16.2-2e66dda: digest: sha256:ce04d7f5d8a96a82c9a7197394c86e60146350e21408b4eed03f868c2cbfeedc size: 856
    --- IMAGETOOLS INSPECT ---
    Name:      ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda
    MediaType: application/vnd.oci.image.index.v1+json
    Digest:    sha256:ce04d7f5d8a96a82c9a7197394c86e60146350e21408b4eed03f868c2cbfeedc
               
    Manifests: 
      Name:        ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda@sha256:04583f14a632935242fb92ee713d86fcecec698afbb2b9fd29f19b08a455d0a6
      MediaType:   application/vnd.oci.image.manifest.v1+json
      Platform:    linux/amd64
                   
      Name:        ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda@sha256:bb044c37fbb3820f5764f001641b1731af27b07678be6ff0f49388b08b33373b
      MediaType:   application/vnd.oci.image.manifest.v1+json
      Platform:    unknown/unknown
      Annotations: 
        vnd.docker.reference.digest: sha256:04583f14a632935242fb92ee713d86fcecec698afbb2b9fd29f19b08a455d0a6
        vnd.docker.reference.type:   attestation-manifest
    REMOTE_DIGEST=sha256:ce04d7f5d8a96a82c9a7197394c86e60146350e21408b4eed03f868c2cbfeedc
    GH_API_TAG_MATCHES=1
```

## Hand-off a Coord Ag 2B (Windows)

David ejecuta en host Windows con estos inputs:

- TAG_BUILT: `o16.2-2e66dda`
- REMOTE_DIGEST: `sha256:ce04d7f5d8a96a82c9a7197394c86e60146350e21408b4eed03f868c2cbfeedc`
- IMAGE_FULL: `ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda`

Comando objetivo (Coord Ag 2B):
`az containerapp job update -g rg-umbral-agents-prod -n aeco-source-crawler --image ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda`

## Prohibiciones cumplidas

- [x] No retagueé `:latest`.
- [x] No retagueé `:v1`.
- [x] No buildié `aeco-pdf-parser` ni `aeco-index-pipeline`.
- [x] No usé `az`.
- [x] No toqué runtime VPS (gateway/dispatcher/worker).
- [x] No escribí en Notion.
- [x] No toqué n8n.
- [x] No toqué PRs RRSS Wave 2.A.
- [x] No expuse `GHCR_PAT` ni tokens en el log.

## Estado

Status `done-vps-side`. NO mergear este PR. Espera a que Coord Ag 2B
cierre PASS para que David decida si flipea a `done` o lo cierra sin
merge (el contenido es solo log de evidencia).
