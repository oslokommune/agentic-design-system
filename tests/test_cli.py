"""The CLI is the agent-facing surface: exit codes and machine-readable errors."""

from __future__ import annotations

import json

from conftest import SPEC_ROOT, patch_json
from ds_compiler.cli import main


def test_check_passes(capsys):
    assert main(["--check", "--spec", str(SPEC_ROOT)]) == 0
    assert "spec OK" in capsys.readouterr().out


def test_compile_writes_app(tmp_path, capsys):
    assert main(["--spec", str(SPEC_ROOT), "--out", str(tmp_path / "out"), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["components"] == ["alert", "button", "card", "tag"]
    assert (tmp_path / "out" / "ds" / "templatetags" / "ds.py").is_file()


def test_custom_app_name(tmp_path):
    assert main(["--spec", str(SPEC_ROOT), "--out", str(tmp_path), "--app-name", "design"]) == 0
    assert (tmp_path / "design" / "spec.py").is_file()


def test_broken_spec_exits_nonzero_with_json_errors(spec_copy, capsys):
    spec_root = spec_copy()
    patch_json(
        spec_root / "components" / "button.json",
        lambda data: data["anatomy"]["styles"].update({"gap": "4px"}),
    )
    assert main(["--check", "--spec", str(spec_root), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error_count"] >= 1
    assert payload["errors"][0]["code"] == "css-raw-literal"
    assert "button.json" in payload["errors"][0]["location"]


def test_broken_spec_prints_human_errors(spec_copy, capsys):
    spec_root = spec_copy()
    patch_json(
        spec_root / "components" / "card.json",
        lambda data: data.__setitem__("composition", []),
    )
    assert main(["--check", "--spec", str(spec_root)]) == 1
    captured = capsys.readouterr()
    assert "FAILED" in captured.err
    assert "composition-mismatch" in captured.err


def test_missing_spec_root_is_an_error(tmp_path, capsys):
    assert main(["--check", "--spec", str(tmp_path / "nope")]) == 1
    assert "spec-root-missing" in capsys.readouterr().err
