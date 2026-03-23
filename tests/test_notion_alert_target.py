from scripts.notion_alert_target import resolve_alert_target


def test_resolve_prefers_direct_supervisor_route():
    env = {
        "NOTION_SUPERVISOR_ALERT_PAGE_ID": "alert-page",
        "NOTION_SUPERVISOR_API_KEY": "supervisor-token",
        "NOTION_CONTROL_ROOM_PAGE_ID": "control-page",
        "NOTION_API_KEY": "worker-token",
    }

    def probe(page_id, token):
        if page_id == "alert-page" and token == "supervisor-token":
            return {"ok": True, "reason": "ok", "archived": False, "in_trash": False}
        return {"ok": False, "reason": "not_used"}

    result = resolve_alert_target(env, page_probe=probe)

    assert result["ok"] is True
    assert result["mode"] == "direct_supervisor"
    assert result["target_page_id"] == "alert-page"


def test_resolve_falls_back_to_worker_control_room_when_alert_page_archived():
    env = {
        "NOTION_SUPERVISOR_ALERT_PAGE_ID": "alert-page",
        "NOTION_SUPERVISOR_API_KEY": "supervisor-token",
        "NOTION_CONTROL_ROOM_PAGE_ID": "control-page",
        "NOTION_API_KEY": "worker-token",
    }

    def probe(page_id, token):
        if page_id == "alert-page":
            return {"ok": False, "reason": "archived", "archived": True, "in_trash": True}
        if page_id == "control-page" and token == "worker-token":
            return {"ok": True, "reason": "ok", "archived": False, "in_trash": False}
        return {"ok": False, "reason": "http_error"}

    result = resolve_alert_target(env, page_probe=probe)

    assert result["ok"] is True
    assert result["mode"] == "worker_control_room_fallback"
    assert result["target_page_id"] == "control-page"
    assert result["reason"] == "archived"


def test_resolve_uses_worker_alert_page_when_supervisor_token_missing():
    env = {
        "NOTION_SUPERVISOR_ALERT_PAGE_ID": "alert-page",
        "NOTION_CONTROL_ROOM_PAGE_ID": "control-page",
        "NOTION_API_KEY": "worker-token",
    }

    def probe(page_id, token):
        if page_id == "alert-page" and token == "worker-token":
            return {"ok": True, "reason": "ok", "archived": False, "in_trash": False}
        return {"ok": False, "reason": "missing_token"}

    result = resolve_alert_target(env, page_probe=probe)

    assert result["ok"] is True
    assert result["mode"] == "worker_alert_page"
    assert result["target_page_id"] == "alert-page"


def test_resolve_reports_unavailable_when_no_active_target_exists():
    env = {
        "NOTION_SUPERVISOR_ALERT_PAGE_ID": "alert-page",
        "NOTION_SUPERVISOR_API_KEY": "supervisor-token",
        "NOTION_CONTROL_ROOM_PAGE_ID": "control-page",
        "NOTION_API_KEY": "worker-token",
    }

    def probe(page_id, token):
        return {"ok": False, "reason": "http_error"}

    result = resolve_alert_target(env, page_probe=probe)

    assert result["ok"] is False
    assert result["mode"] == "unavailable"
    assert result["reason"] == "no_active_notion_target"
