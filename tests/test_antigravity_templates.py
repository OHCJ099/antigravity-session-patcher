import json


def test_antigravity_builtin_templates_include_full_codex_set():
    from codex_session_patcher.ctf_config.templates import BUILTIN_TEMPLATES

    templates = BUILTIN_TEMPLATES["antigravity"]
    names = [tpl["name"] for tpl in templates]

    assert names == [
        "Optimized CTF Workflow",
        "CTF Private Deploy",
        "General Security Testing",
    ]
    assert templates[0]["default"] is True
    for tpl in templates:
        assert "Antigravity" in tpl["prompt"]
        assert "You are Codex" not in tpl["prompt"]


def test_antigravity_templates_migrate_legacy_codex_user_templates(tmp_path, monkeypatch):
    import web.backend.api as api
    from fastapi.testclient import TestClient
    from web.backend.main import app

    config_path = tmp_path / "antigravity-session-patcher" / "config.json"
    monkeypatch.setattr(api, "DEFAULT_CONFIG_FILE", str(config_path))
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({
        "ctf_templates": {
            "codex": [
                {
                    "name": "Legacy Custom",
                    "prompt": "You are Codex in a custom CTF profile.",
                }
            ]
        }
    }), encoding="utf-8")

    client = TestClient(app)
    response = client.get("/api/ctf/prompt/antigravity/templates")

    assert response.status_code == 200
    templates = response.json()["templates"]
    assert [tpl["name"] for tpl in templates[:3]] == [
        "Optimized CTF Workflow",
        "CTF Private Deploy",
        "General Security Testing",
    ]
    assert any(tpl["name"] == "Legacy Custom" for tpl in templates)

    prompt_response = client.get("/api/ctf/prompt/antigravity/templates/Legacy%20Custom")
    assert prompt_response.status_code == 200
    prompt = prompt_response.json()["prompt"]
    assert "You are Antigravity" in prompt
    assert "You are Codex" not in prompt

    persisted = json.loads(config_path.read_text(encoding="utf-8"))
    migrated = persisted["ctf_templates"]["antigravity"][0]
    assert migrated["name"] == "Legacy Custom"
    assert migrated["migrated_from"] == "codex"
