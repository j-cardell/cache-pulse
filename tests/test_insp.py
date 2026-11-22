"""Contract tests for cache_pulse.inspector (run after inspector.py lands)."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def test_fake_hf_tree(tmp_path, monkeypatch):
    hf = tmp_path / "hf"
    refs = hf / "hub" / "models--org--model" / "refs"
    refs.mkdir(parents=True)
    (refs / "a.bin").write_bytes(b"x" * 100)
    (refs / "b.bin").write_bytes(b"y" * 200)
    monkeypatch.setenv("HF_HOME", str(hf))
    from cache_pulse.inspector import get_cache_dirs, list_hf_models

    assert get_cache_dirs()["hf"] == hf
    assert list_hf_models(hf) == [{"name": "org/model", "size": 300, "files": 2}]


def test_missing_dirs(tmp_path):
    from cache_pulse.inspector import list_hf_models, list_torch_caches

    assert list_hf_models(tmp_path / "nope") == []
    assert list_torch_caches(tmp_path / "nope") == []


def test_fake_podman(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "podman"
    script.write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        '  --version) echo "podman version 5.99.0-fake";;\n'
        '  info) printf \'{"Host": {"Security": {"Rootless": true}}}\n\';;\n'
        "esac\n"
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    from cache_pulse.inspector import check_container_runtime

    r = check_container_runtime()
    assert r["available"] is True
    assert r["name"] == "podman"
    assert r["version"] == "5.99.0-fake"
    assert r["rootless"] is True


def test_load_config(tmp_path):
    from cache_pulse.inspector import load_config

    cfg = {
        "webhook_url": "https://example.test/hook",
        "api_token": "tok123",
        "disk_threshold": 0.85,
    }
    (tmp_path / "cfg.json").write_text(json.dumps(cfg))
    loaded = load_config(tmp_path / "cfg.json")
    assert loaded["webhook_url"] == "https://example.test/hook"
    assert loaded["api_token"] == "tok123"
    assert loaded["disk_threshold"] == 0.85
    assert load_config(tmp_path / "missing.json") == {}


def test_send_alert(tmp_path):
    import cache_pulse.inspector as insp

    class Handler(BaseHTTPRequestHandler):
        records = []

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            Handler.records.append({"path": self.path, "body": body, "headers": dict(self.headers)})
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}"
        assert insp.send_alert(url, "tok123", {"type": "test"}) is True
        assert json.loads(Handler.records[0]["body"]) == {"type": "test"}
        assert Handler.records[0]["headers"]["Authorization"] == "Bearer tok123"

        assert insp.send_alert(url, None, {}) is True
        assert "Authorization" not in Handler.records[1]["headers"]
    finally:
        server.shutdown()
        server.server_close()
