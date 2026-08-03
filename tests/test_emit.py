"""What the compiler emits: CSS with no literals, a self-contained Django app,
and byte-identical output for identical input (so diffs are meaningful)."""

from __future__ import annotations

import re

from ds_compiler import compile_spec
from conftest import SPEC_ROOT

HEX_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b")
UNIT_LITERAL = re.compile(r"(?<![-\w])\d*\.?\d+(px|rem|em|%|vh|vw)\b")


def test_app_layout(compiled):
    app = compiled.app_dir
    for relative in (
        "__init__.py",
        "apps.py",
        "runtime.py",
        "spec.py",
        "templatetags/__init__.py",
        "templatetags/ds.py",
        "templates/ds/button.html",
        "templates/ds/tag.html",
        "templates/ds/alert.html",
        "templates/ds/card.html",
        "static/ds/tokens.css",
        "static/ds/components.css",
    ):
        assert (app / relative).is_file(), relative
    assert compiled.overrides_report.is_file()


def test_tokens_css_declares_custom_properties_and_keeps_aliases(compiled):
    css = (compiled.app_dir / "static" / "ds" / "tokens.css").read_text()
    assert ":root {" in css
    # Base scale holds the literal...
    assert "--ds-color-base-blue-600: #1d4ed8;" in css
    # ...and semantic tokens stay aliases in CSS too.
    assert "--ds-color-action-primary: var(--ds-color-base-blue-600);" in css
    assert "--ds-size-spacing-md: 0.75rem;" in css
    assert "--ds-font-weight-bold: 700;" in css
    assert '--ds-font-family-sans: Inter, "Helvetica Neue", Arial, sans-serif;' in css


def test_every_token_reaches_the_stylesheet(compiled):
    css = (compiled.app_dir / "static" / "ds" / "tokens.css").read_text()
    for token in compiled.spec.tokens:
        assert f"{token.css_var}:" in css


def test_components_css_contains_no_literals(compiled):
    css = (compiled.app_dir / "static" / "ds" / "components.css").read_text()
    declarations = [
        line for line in css.splitlines() if ":" in line and not line.strip().startswith(("/*", "*"))
    ]
    assert declarations
    for line in declarations:
        value = line.split(":", 1)[1]
        assert not HEX_LITERAL.search(value), line
        assert not UNIT_LITERAL.search(value), line


def test_components_css_uses_bem_selectors(compiled):
    css = (compiled.app_dir / "static" / "ds" / "components.css").read_text()
    assert ".ds-button {" in css
    assert ".ds-button--primary {" in css
    assert ".ds-button--primary:hover {" in css
    assert ".ds-button:disabled {" in css
    assert ".ds-button__label {" in css
    # Modifier styles that live on a part compile to a descendant selector.
    assert ".ds-alert--danger .ds-alert__icon {" in css


def test_spec_module_carries_prop_metadata(compiled):
    namespace: dict = {}
    exec((compiled.app_dir / "spec.py").read_text(), namespace)
    components = namespace["COMPONENTS"]
    assert set(components) == {"button", "tag", "alert", "card"}
    assert components["button"]["props"]["variant"]["values"] == ["primary", "secondary"]
    assert components["button"]["props"]["label"]["required"] is True
    assert components["button"]["block"] is False
    assert components["card"]["block"] is True
    assert components["card"]["slots"] == ["heading", "default"]
    assert namespace["TOKEN_VARS"]["color.action.primary"] == "--ds-color-action-primary"


def test_templatetags_module_registers_one_tag_per_component(compiled):
    source = (compiled.app_dir / "templatetags" / "ds.py").read_text()
    for tag in ("ds_button", "ds_tag", "ds_alert", "ds_card", "ds_slot"):
        assert tag in source


def test_output_is_deterministic(tmp_path):
    first = compile_spec([SPEC_ROOT], out_dir=tmp_path / "a")
    second = compile_spec([SPEC_ROOT], out_dir=tmp_path / "b")
    for path in first.written:
        twin = tmp_path / "b" / path.relative_to(tmp_path / "a")
        assert twin.read_bytes() == path.read_bytes(), str(path)
    assert len(first.written) == len(second.written)
