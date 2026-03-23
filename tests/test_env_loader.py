from scripts import env_loader


def test_load_prefers_openclaw_env_before_repo_env(tmp_path, monkeypatch):
    openclaw_env = tmp_path / "openclaw.env"
    repo_env = tmp_path / ".env"
    openclaw_env.write_text("FROM_OPENCLAW=1\nSHARED_KEY=openclaw\n", encoding="utf-8")
    repo_env.write_text("FROM_REPO=1\nSHARED_KEY=repo\n", encoding="utf-8")

    monkeypatch.setattr(env_loader, "_OPENCLAW_ENV_FILE", openclaw_env)
    monkeypatch.setattr(env_loader, "_ENV_FILE", repo_env)
    monkeypatch.setattr(env_loader, "_iter_env_files", lambda: [openclaw_env, repo_env])
    monkeypatch.delenv("FROM_OPENCLAW", raising=False)
    monkeypatch.delenv("FROM_REPO", raising=False)
    monkeypatch.delenv("SHARED_KEY", raising=False)

    env_loader.load()

    assert env_loader.os.environ["FROM_OPENCLAW"] == "1"
    assert env_loader.os.environ["FROM_REPO"] == "1"
    assert env_loader.os.environ["SHARED_KEY"] == "openclaw"


def test_load_does_not_override_existing_process_env(tmp_path, monkeypatch):
    repo_env = tmp_path / ".env"
    repo_env.write_text("EXISTING_KEY=from-file\n", encoding="utf-8")

    monkeypatch.setattr(env_loader, "_ENV_FILE", repo_env)
    monkeypatch.setattr(env_loader, "_iter_env_files", lambda: [repo_env])
    monkeypatch.setenv("EXISTING_KEY", "from-process")

    env_loader.load()

    assert env_loader.os.environ["EXISTING_KEY"] == "from-process"
