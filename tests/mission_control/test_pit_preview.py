"""Tests de routes/pit_preview.py — preview seguro de prototipos (PIT-5 P5.3).

Un test por guard del plan §4 P5.3 (opción A):

- traversal (`..` / `%2e%2e`) → 403
- symlink que escapa del vault → 403
- firma vencida / inválida / de otro scope → 403; ausente → 401
- extensión fuera de allowlist → 403
- happy path html + css + js relativo (firma → cookie HttpOnly path-scoped)
- alias /pit-preview/* → redirect a la canónica (3 formatos del announce P5.0)
- la cookie de preview NO da acceso a las rutas JSON bearer-only
- fail-closed 503 sin MISSION_CONTROL_TOKEN

Vault sintético en tmp_path — jamás se lee un vault real.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import mission_control.auth as mc_auth
from tests.mission_control._pit_fixtures import (
    ARCHIVED_PIT_ID,
    DEMO_PIT_ID,
    TOKEN,
    build_demo_vault,
    build_evidence,
)

AUTH = {"Authorization": f"Bearer {TOKEN}"}
PREFIX = f"/pit/preview/{DEMO_PIT_ID}/lane-alpha/2/"
LINK = f"/pit/tournaments/{DEMO_PIT_ID}/lanes/lane-alpha/iterations/2/preview-link"

INDEX_HTML = (
    "<html><head><link rel=\"stylesheet\" href=\"style.css\">"
    "<script src=\"app.js\"></script></head><body>demo-proto</body></html>"
)


def _reload_app():
    import mission_control.config as cfg

    importlib.reload(cfg)
    import mission_control.auth as auth

    importlib.reload(auth)
    import mission_control.app as app_module

    importlib.reload(app_module)
    return app_module


def _enrich_prototype(vault, tmp_path) -> None:
    """Suma al prototype de lane-alpha iter 2: assets, extensión prohibida,
    subdir, y un symlink que escapa del vault (vectores de ataque)."""
    proto = (
        vault
        / "pit"
        / DEMO_PIT_ID
        / "lanes"
        / "lane-alpha"
        / "iterations"
        / "2"
        / "prototype"
    )
    (proto / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (proto / "style.css").write_text("body { color: #c9d1d9; }", encoding="utf-8")
    (proto / "app.js").write_text("console.log('ok');", encoding="utf-8")
    (proto / "prototype-meta.json").write_text('{"lane": "alpha"}', encoding="utf-8")
    (proto / "notes.exe").write_bytes(b"MZ\x90\x00")
    assets = proto / "assets"
    assets.mkdir()
    (assets / "logo.svg").write_text("<svg></svg>", encoding="utf-8")
    secret = tmp_path / "outside-vault-secret.html"
    secret.write_text("<html>SECRET</html>", encoding="utf-8")
    (proto / "escape.html").symlink_to(secret)
    # Torneo archivado CON prototype: el preview solo sirve el subtree pit/.
    archived_proto = (
        vault
        / "archive"
        / ARCHIVED_PIT_ID
        / "lanes"
        / "lane-winner"
        / "iterations"
        / "1"
        / "prototype"
    )
    archived_proto.mkdir(parents=True)
    (archived_proto / "index.html").write_text("<html>old</html>", encoding="utf-8")


@pytest.fixture
def client(monkeypatch, tmp_path):
    vault = build_demo_vault(tmp_path / "vault")
    _enrich_prototype(vault, tmp_path)
    evidence = build_evidence(tmp_path / "evidence")
    fallback = tmp_path / "examples"
    fallback.mkdir()
    monkeypatch.setenv("MISSION_CONTROL_TOKEN", TOKEN)
    monkeypatch.setenv("PIT_VAULT_PATH", str(vault))
    monkeypatch.setenv("PIT_EVIDENCE_DIR", str(evidence))
    monkeypatch.setenv("PIT_SPEC_FALLBACK_DIR", str(fallback))
    app_module = _reload_app()
    return TestClient(app_module.app)


@pytest.fixture
def no_token_client(monkeypatch, tmp_path):
    vault = build_demo_vault(tmp_path / "vault")
    monkeypatch.delenv("MISSION_CONTROL_TOKEN", raising=False)
    monkeypatch.setenv("PIT_VAULT_PATH", str(vault))
    monkeypatch.setenv("PIT_EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("PIT_SPEC_FALLBACK_DIR", str(tmp_path / "examples"))
    app_module = _reload_app()
    return TestClient(app_module.app)


def _signed_url(client) -> str:
    res = client.get(LINK, headers=AUTH)
    assert res.status_code == 200
    return res.json()["url"]


def _sig_for(scope: str, ttl_seconds: int = 900) -> str:
    token_value, _ = mc_auth.make_preview_sig(scope, ttl_seconds)
    return token_value


# ---------------------------------------------------------------------------
# preview-link (bearer)
# ---------------------------------------------------------------------------


def test_preview_link_requires_bearer(client):
    assert client.get(LINK).status_code == 401


def test_preview_link_rejects_wrong_bearer(client):
    res = client.get(LINK, headers={"Authorization": "Bearer wrong"})
    assert res.status_code == 403


def test_preview_link_emits_signed_url_with_expiry(client):
    body = client.get(LINK, headers=AUTH).json()
    assert body["url"].startswith(f"{PREFIX}?t=")
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert expires_at > datetime.now(tz=timezone.utc)


def test_preview_link_404_without_prototype(client):
    res = client.get(
        f"/pit/tournaments/{DEMO_PIT_ID}/lanes/lane-gamma/iterations/1/preview-link",
        headers=AUTH,
    )
    assert res.status_code == 404


def test_preview_link_422_invalid_ids(client):
    bad_lane = f"/pit/tournaments/{DEMO_PIT_ID}/lanes/EVIL/iterations/2/preview-link"
    assert client.get(bad_lane, headers=AUTH).status_code == 422
    bad_pit = "/pit/tournaments/PIT-X/lanes/lane-alpha/iterations/2/preview-link"
    assert client.get(bad_pit, headers=AUTH).status_code == 422


# ---------------------------------------------------------------------------
# Firma + cookie (guard 6)
# ---------------------------------------------------------------------------


def test_signed_url_redirects_to_entry_and_sets_scoped_cookie(client):
    url = _signed_url(client)
    res = client.get(url, follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == f"{PREFIX}index.html"
    cookie = res.headers["set-cookie"]
    assert "pit_preview=" in cookie
    assert "HttpOnly" in cookie
    assert f"Path={PREFIX}" in cookie
    assert "SameSite=strict" in cookie.lower() or "samesite=strict" in cookie.lower()


def test_happy_path_html_css_js_relative(client):
    url = _signed_url(client)
    # Primer hit firmado → redirect a index.html con cookie en el jar.
    res = client.get(url)
    assert res.status_code == 200
    assert "demo-proto" in res.text
    assert res.headers["content-type"].startswith("text/html")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'self'" in res.headers["content-security-policy"]
    # Assets relativos: la cookie path-scoped autentica sin firma ni bearer.
    css = client.get(f"{PREFIX}style.css")
    assert css.status_code == 200
    assert css.headers["content-type"].startswith("text/css")
    assert "content-security-policy" not in css.headers
    js = client.get(f"{PREFIX}app.js")
    assert js.status_code == 200
    assert js.headers["content-type"].startswith("text/javascript")
    svg = client.get(f"{PREFIX}assets/logo.svg")
    assert svg.status_code == 200
    assert svg.headers["content-type"].startswith("image/svg+xml")
    meta = client.get(f"{PREFIX}prototype-meta.json")
    assert meta.status_code == 200
    assert meta.headers["content-type"].startswith("application/json")


def test_default_entry_without_index(client):
    # lane-beta iter 1 solo tiene demo.html → entry = primer .html ordenado.
    res = client.get(
        f"/pit/tournaments/{DEMO_PIT_ID}/lanes/lane-beta/iterations/1/preview-link",
        headers=AUTH,
    )
    url = res.json()["url"]
    redirect = client.get(url, follow_redirects=False)
    assert redirect.status_code == 302
    assert redirect.headers["location"].endswith("/demo.html")


def test_missing_credentials_401(client):
    assert client.get(f"{PREFIX}index.html").status_code == 401


def test_expired_signature_403(client):
    expired = _sig_for(f"{DEMO_PIT_ID}/lane-alpha/2", ttl_seconds=-60)
    res = client.get(f"{PREFIX}?t={expired}")
    assert res.status_code == 403


def test_invalid_signature_403(client):
    valid = _sig_for(f"{DEMO_PIT_ID}/lane-alpha/2")
    expiry, _, sig = valid.partition(".")
    tampered = f"{expiry}.{'0' * len(sig)}"
    assert client.get(f"{PREFIX}?t={tampered}").status_code == 403
    assert client.get(f"{PREFIX}?t=garbage").status_code == 403


def test_signature_scope_mismatch_403(client):
    other_scope = _sig_for(f"{DEMO_PIT_ID}/lane-beta/1")
    assert client.get(f"{PREFIX}?t={other_scope}").status_code == 403


def test_invalid_cookie_403(client):
    res = client.get(
        f"{PREFIX}index.html", headers={"Cookie": "pit_preview=123.deadbeef"}
    )
    assert res.status_code == 403


def test_preview_cookie_does_not_grant_json_endpoints(client):
    """Aislamiento: la cookie de preview NO autentica las rutas bearer-only."""
    sig = _sig_for(f"{DEMO_PIT_ID}/lane-alpha/2")
    for route in ("/pit/tournaments", f"/pit/tournaments/{DEMO_PIT_ID}", "/agents"):
        res = client.get(route, headers={"Cookie": f"pit_preview={sig}"})
        assert res.status_code == 401, route


def test_token_unset_fails_closed_503(no_token_client):
    res = no_token_client.get(f"{PREFIX}index.html")
    assert res.status_code == 503


# ---------------------------------------------------------------------------
# Path guards (1, 2, 3, 4)
# ---------------------------------------------------------------------------


def test_traversal_encoded_dotdot_403(client):
    sig = _sig_for(f"{DEMO_PIT_ID}/lane-alpha/2")
    res = client.get(f"{PREFIX}%2e%2e/%2e%2e/%2e%2e/spec/pit_spec.yaml?t={sig}")
    assert res.status_code == 403
    res = client.get(f"{PREFIX}%2e%2e%2f%2e%2e%2fsecret.html?t={sig}")
    assert res.status_code == 403


def test_traversal_inside_allowed_extension_403(client):
    # Extensión permitida pero path que escapa → lo corta el realpath guard.
    sig = _sig_for(f"{DEMO_PIT_ID}/lane-alpha/2")
    res = client.get(
        f"{PREFIX}assets/%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/outside.html?t={sig}"
    )
    assert res.status_code == 403


def test_symlink_escape_403(client):
    url = _signed_url(client)
    client.get(url)  # establece cookie válida
    res = client.get(f"{PREFIX}escape.html")
    assert res.status_code == 403
    assert "SECRET" not in res.text


def test_forbidden_extension_403(client):
    url = _signed_url(client)
    client.get(url)
    res = client.get(f"{PREFIX}notes.exe")
    assert res.status_code == 403


def test_no_directory_listing(client):
    url = _signed_url(client)
    client.get(url)
    res = client.get(f"{PREFIX}assets/")
    assert res.status_code == 403  # sin extensión → allowlist corta antes
    assert "logo.svg" not in res.text


def test_invalid_ids_422_before_auth_and_fs(client):
    # Guard 2: regex falla → 422 incluso sin credenciales.
    assert client.get("/pit/preview/PIT-X/lane-alpha/2/").status_code == 422
    assert client.get(f"/pit/preview/{DEMO_PIT_ID}/evil/2/").status_code == 422


def test_iteration_out_of_range_422(client):
    assert client.get(f"/pit/preview/{DEMO_PIT_ID}/lane-alpha/0/").status_code == 422
    assert client.get(f"/pit/preview/{DEMO_PIT_ID}/lane-alpha/11/").status_code == 422


def test_unknown_iteration_404(client):
    sig = _sig_for(f"{DEMO_PIT_ID}/lane-alpha/3")
    res = client.get(f"/pit/preview/{DEMO_PIT_ID}/lane-alpha/3/?t={sig}")
    assert res.status_code == 404


def test_missing_file_404(client):
    url = _signed_url(client)
    client.get(url)
    assert client.get(f"{PREFIX}missing.css").status_code == 404


def test_archived_tournament_not_served(client):
    # El preview solo sirve <vault>/pit/ — archive/ queda fuera (regla 1).
    link = (
        f"/pit/tournaments/{ARCHIVED_PIT_ID}/lanes/lane-winner/iterations/1/preview-link"
    )
    assert client.get(link, headers=AUTH).status_code == 404
    sig = _sig_for(f"{ARCHIVED_PIT_ID}/lane-winner/1")
    res = client.get(f"/pit/preview/{ARCHIVED_PIT_ID}/lane-winner/1/?t={sig}")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Alias /pit-preview/* → canónica (formatos del announce P5.0)
# ---------------------------------------------------------------------------


def test_alias_iterations_prototype_file(client):
    res = client.get(
        f"/pit-preview/{DEMO_PIT_ID}/lane-alpha/iterations/2/prototype/index.html?t=x",
        follow_redirects=False,
    )
    assert res.status_code == 307
    assert res.headers["location"] == f"{PREFIX}index.html?t=x"


def test_alias_iter_dash(client):
    res = client.get(
        f"/pit-preview/{DEMO_PIT_ID}/lane-alpha/iter-2", follow_redirects=False
    )
    assert res.status_code == 307
    assert res.headers["location"] == PREFIX


def test_alias_iteration_dash(client):
    res = client.get(
        f"/pit-preview/{DEMO_PIT_ID}/lane-alpha/iteration-2", follow_redirects=False
    )
    assert res.status_code == 307
    assert res.headers["location"] == PREFIX


def test_alias_unrecognized_format_404(client):
    res = client.get(
        f"/pit-preview/{DEMO_PIT_ID}/lane-alpha/whatever", follow_redirects=False
    )
    assert res.status_code == 404


def test_alias_invalid_ids_422(client):
    res = client.get(
        "/pit-preview/PIT-X/lane-alpha/iter-2", follow_redirects=False
    )
    assert res.status_code == 422


def test_alias_end_to_end_with_signature(client):
    """URL estilo announce del piloto + firma → sirve el HTML real."""
    sig = _sig_for(f"{DEMO_PIT_ID}/lane-alpha/2")
    res = client.get(
        f"/pit-preview/{DEMO_PIT_ID}/lane-alpha/iterations/2/prototype/index.html"
        f"?t={sig}"
    )
    assert res.status_code == 200
    assert "demo-proto" in res.text


# ---------------------------------------------------------------------------
# No-regresión: JSON /pit/* sigue bearer-only y funcional
# ---------------------------------------------------------------------------


def test_pit_json_namespace_unaffected(client):
    body = client.get("/pit/tournaments", headers=AUTH).json()
    assert body["read_only"] is True
    assert DEMO_PIT_ID in {t["pit_id"] for t in body["tournaments"]}
