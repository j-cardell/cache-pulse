"""Tests for cache_pulse.renderer."""
from cache_pulse.renderer import human_size, render_report


def make_data() -> dict:
    return {
        "generated_at": "2026-11-21T12:00:00+00:00",
        "host": "myhost",
        "hf": {
            "dir": "/home/x/.cache/huggingface",
            "models": [
                {"name": "org/model-a", "size": 123456789, "files": 42},
                {"name": "org/model-b", "size": 555, "files": 7},
            ],
            "total_size": 123456789,
        },
        "torch": {
            "dir": "/home/x/.cache/torch",
            "caches": [{"name": "hub", "size": 999, "files": 3}],
            "total_size": 999,
        },
        "container": {
            "available": True,
            "name": "podman",
            "version": "5.99.0",
            "rootless": True,
            "error": None,
        },
        "disk": {
            "path": "/home/x",
            "total": 500000000000,
            "used": 300000000000,
            "free": 200000000000,
        },
    }


def test_render_report_writes_file(tmp_path):
    out = render_report(make_data(), tmp_path / "out")
    assert out == tmp_path / "out" / "latest.html"
    assert out.exists()
    assert out.stat().st_size > 0


def test_no_unsubstituted_placeholders(tmp_path):
    text = render_report(make_data(), tmp_path / "out").read_text(encoding="utf-8")
    placeholders = (
        "$TITLE",
        "$HF_MODELS",
        "$TORCH_CACHES",
        "$CONTAINER",
        "$DISK",
        "$TOTAL_SIZE",
        "$GENERATED_AT",
    )
    for ph in placeholders:
        assert ph not in text


def test_html_escaping(tmp_path):
    data = make_data()
    data["hf"]["models"].append({"name": "<script>alert(1)</script>", "size": 10, "files": 1})
    text = render_report(data, tmp_path / "out").read_text(encoding="utf-8")
    assert "&lt;script&gt;" in text
    assert "<script>alert" not in text


def test_human_size():
    assert human_size(0) == "0 B"
    assert human_size(1023) == "1023 B"
    assert human_size(1536) == "1.5 KB"
    assert human_size(5 * 1024**3) == "5.0 GB"


def test_empty_models(tmp_path):
    data = make_data()
    data["hf"]["models"] = []
    out = render_report(data, tmp_path / "out")
    assert out.exists()
    assert out.stat().st_size > 0
