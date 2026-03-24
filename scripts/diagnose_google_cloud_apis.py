#!/usr/bin/env python3
"""
Diagnóstico operativo de búsqueda/Google APIs para Rick.

Tavily es el backend de búsqueda primario del stack. Google Custom Search se
mantiene solo como chequeo legado/experimental porque suele devolver 403 en
proyectos nuevos o sin acceso histórico.

Carga variables desde .env en la raíz del repo. No imprime claves.
Ejecutar: cd repo_root && python scripts/diagnose_google_cloud_apis.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

# Cargar variables desde .env (o usar las ya definidas en el sistema)
try:
    from scripts.env_loader import load as load_env
    load_env()
except ImportError:
    env_file = repo_root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'").replace("\x00", "")
            if k and "\x00" not in k:
                os.environ.setdefault(k, v)

def mask(s: str) -> str:
    if not s or len(s) < 8:
        return "***"
    return s[:4] + "..." + s[-4:]

def test_custom_search() -> None:
    key = os.environ.get("GOOGLE_CSE_API_KEY_RICK_UMBRAL") or os.environ.get("GOOGLE_CSE_API_KEY")
    cx = os.environ.get("GOOGLE_CSE_CX")
    if not key:
        print("Custom Search (legado): SKIP (falta GOOGLE_CSE_API_KEY_RICK_UMBRAL o GOOGLE_CSE_API_KEY)")
        return
    if not cx:
        print("Custom Search (legado): SKIP (falta GOOGLE_CSE_CX)")
        return
    try:
        import urllib.request
        import urllib.error
        import json
        url = (
            "https://www.googleapis.com/customsearch/v1"
            f"?key={key}&cx={cx}&q=test&num=1"
        )
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode()
            if "items" in data or "searchInformation" in data:
                print("Custom Search (legado): OK (200)")
            else:
                print("Custom Search (legado): 200 pero respuesta inesperada")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()
        except Exception:
            pass
        err = str(e)
        if e.code == 403:
            print("Custom Search (legado): 403 - Proyecto sin acceso a Custom Search JSON API.")
            if body:
                try:
                    j = json.loads(body)
                    msg = j.get("error", {}).get("message", body[:200])
                    print("  Mensaje API:", msg)
                except Exception:
                    print("  Mensaje API:", body[:300])
            print("  Este resultado no bloquea el path operativo: web_discovery usa Tavily por defecto.")
            print("  Solo vale la pena insistir si quieres mantener un path legado en un proyecto grandfathered.")
        elif e.code == 401:
            print("Custom Search (legado): 401 - Key invalida o restricciones (IP/API).")
        else:
            print(f"Custom Search (legado): ERROR {e.code} - {body[:200] if body else err[:200]}")
    except Exception as e:
        err = str(e)
        if "403" in err:
            print("Custom Search (legado): 403 - El proyecto no tiene acceso a Custom Search JSON API.")
            print("  Este resultado no bloquea el path operativo: web_discovery usa Tavily por defecto.")
        elif "401" in err:
            print("Custom Search (legado): 401 - Key invalida o restricciones (IP/API).")
        else:
            print("Custom Search (legado): ERROR -", err[:200])

def test_gemini_ai_studio() -> None:
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY_RICK_UMBRAL")
    if not key:
        print("Gemini (AI Studio): SKIP (falta GOOGLE_API_KEY)")
        return
    try:
        import urllib.request
        import json
        url = "https://generativelanguage.googleapis.com/v1beta/models?key=" + key
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            if "models" in data:
                print("Gemini (AI Studio / generativelanguage): OK (200)")
            else:
                print("Gemini: 200 pero sin 'models' en respuesta")
    except Exception as e:
        err = str(e)
        if "401" in err:
            print("Gemini (AI Studio): 401 - Key invalida o no es de Google AI Studio.")
            print("  Para Vertex usa Service Account; para AI Studio usa key de aistudio.google.com")
        elif "403" in err:
            print("Gemini: 403 - Proyecto sin acceso o API no habilitada.")
        else:
            print(f"Gemini: ERROR — {err[:200]}")


def test_gemini_grounded_search() -> None:
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY_NANO")
    if not key:
        print("Gemini grounded search: SKIP (falta GOOGLE_API_KEY / GOOGLE_API_KEY_NANO)")
        return
    try:
        import urllib.request
        import json

        payload = {
            "contents": [{"role": "user", "parts": [{"text": "Busca una noticia reciente sobre BIM en Latinoamérica y responde en una frase."}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 128},
        }
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + key,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
            meta = (data.get("candidates") or [{}])[0].get("groundingMetadata", {}) or {}
            if meta.get("webSearchQueries"):
                print("Gemini grounded search: OK (200) — google_search activo")
            else:
                print("Gemini grounded search: 200 pero sin webSearchQueries")
    except Exception as e:
        err = str(e)
        if "401" in err:
            print("Gemini grounded search: 401 - Key invalida o sin permisos.")
        elif "403" in err:
            print("Gemini grounded search: 403 - Proyecto sin acceso o API no habilitada.")
        else:
            print(f"Gemini grounded search: ERROR - {err[:200]}")

def test_tavily_search() -> None:
    """Tavily es el backend operativo primario de web_discovery."""
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        print("Tavily Search: SKIP (falta TAVILY_API_KEY)")
        return
    try:
        import urllib.request
        import json
        body = json.dumps({"query": "test", "max_results": 1}).encode("utf-8")
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key.strip()}"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            if data.get("results") is not None:
                print("Tavily Search: OK (200)")
            else:
                print("Tavily Search: 200 pero sin 'results'")
    except Exception as e:
        err = str(e)
        if "401" in err or "403" in err:
            print("Tavily Search: Key invalida o sin permisos.")
        else:
            print("Tavily Search: ERROR -", err[:150])


def main() -> None:
    print("=== Diagnóstico búsqueda / Google APIs para Rick (leyendo desde .env) ===\n")
    test_tavily_search()
    print()
    test_custom_search()
    print()
    test_gemini_ai_studio()
    print()
    test_gemini_grounded_search()
    print("\n--- Sobre Vertex AI ---")
    print("Vertex requiere OAuth/Service Account (no API key). 400 = formato de request; credencial puede ser valida.")
    print("Para gestión de suscripciones/facturación: Cloud Billing API + Service Account con roles/billing.admin")

if __name__ == "__main__":
    main()
