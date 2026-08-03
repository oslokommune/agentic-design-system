"""The single escape hatch: legal, but recorded in overrides-report.json."""

from __future__ import annotations

import json

import pytest

from conftest import DEMO_SPEC_ROOT, SPEC_ROOT
from ds_compiler import compile_spec
from ds_compiler.django_env import make_engine

OVERRIDE_ID = "ovr.promo-banner.campaign-gradient"
OVERRIDE_CLASS = "ds-o-promo-banner-campaign-gradient"


@pytest.fixture(scope="module")
def demo_compiled(tmp_path_factory):
    """Core spec + the demo spec that uses the escape hatch."""
    out_dir = tmp_path_factory.mktemp("demo_compiled")
    return compile_spec([SPEC_ROOT, DEMO_SPEC_ROOT], out_dir=out_dir, app_name="ds_demo")


def test_core_spec_has_no_overrides(compiled):
    report = json.loads(compiled.overrides_report.read_text())
    assert report["count"] == 0
    assert report["overrides"] == []
    assert report["components_with_overrides"] == []


def test_override_is_recorded_with_location_and_reason(demo_compiled):
    report = json.loads(demo_compiled.overrides_report.read_text())
    assert report["count"] == 1
    assert report["components_with_overrides"] == ["promo-banner"]
    entry = report["overrides"][0]
    assert entry["id"] == OVERRIDE_ID
    assert entry["component"] == "promo-banner"
    assert entry["component_id"] == "cmp.promo-banner"
    assert entry["spec_file"].endswith("promo-banner.json")
    assert entry["node_path"] == "anatomy.children[0]"
    assert entry["selector"] == f".{OVERRIDE_CLASS}"
    assert "gradient" in entry["reason"]
    assert entry["declarations"]["background"].startswith("linear-gradient")
    assert entry["attrs"] == {"data-campaign": "q3"}


def test_override_css_is_emitted_with_its_reason(demo_compiled):
    css = (demo_compiled.app_dir / "static" / "ds" / "components.css").read_text()
    assert f"/* OVERRIDE {OVERRIDE_ID} -" in css
    assert f".{OVERRIDE_CLASS} {{" in css
    assert "linear-gradient(135deg, #ff0080 0%, #7928ca 100%)" in css


def test_override_node_renders_with_a_loud_class(demo_compiled):
    from django.template import Context

    engine = make_engine(demo_compiled.out_dir, app_name="ds_demo")
    html = engine.from_string(
        '{% load ds %}{% ds_promo_banner headline="Sale" cta_label="Buy" note="Only override" %}'
    ).render(Context({}))
    assert "ds-override" in html
    assert OVERRIDE_CLASS in html
    assert 'data-campaign="q3"' in html
    # The override still composes real system components.
    assert "ds-button ds-button--secondary" in html
    assert "ds-alert--info" in html
    assert "Only override" in html


def test_override_requires_a_reason(tmp_path):
    """The override node type is the only place literals are legal - at a price."""
    import shutil

    from ds_compiler import SpecValidationError, load_and_validate
    from conftest import patch_json

    spec_root = tmp_path / "spec"
    shutil.copytree(SPEC_ROOT, spec_root)
    demo_root = tmp_path / "demo-spec"
    shutil.copytree(DEMO_SPEC_ROOT, demo_root)

    patch_json(
        demo_root / "components" / "promo-banner.json",
        lambda data: data["anatomy"]["children"][0].pop("reason"),
    )
    with pytest.raises(SpecValidationError) as excinfo:
        load_and_validate([spec_root, demo_root])
    assert "schema-invalid" in excinfo.value.codes
    assert any("reason" in error.message for error in excinfo.value.errors)


def test_raw_css_outside_an_override_still_fails(tmp_path):
    """Same declarations, no override node -> hard failure."""
    import shutil

    from ds_compiler import SpecValidationError, load_and_validate
    from conftest import patch_json

    spec_root = tmp_path / "spec"
    shutil.copytree(SPEC_ROOT, spec_root)
    demo_root = tmp_path / "demo-spec"
    shutil.copytree(DEMO_SPEC_ROOT, demo_root)

    def to_plain_element(data):
        node = data["anatomy"]["children"][0]
        node["node"] = "element"
        node["styles"] = {"padding": node["css"]["padding"]}
        for key in ("id", "reason", "css"):
            node.pop(key)

    patch_json(demo_root / "components" / "promo-banner.json", to_plain_element)
    with pytest.raises(SpecValidationError) as excinfo:
        load_and_validate([spec_root, demo_root])
    assert "css-raw-literal" in excinfo.value.codes
