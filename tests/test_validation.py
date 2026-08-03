"""The spec must be provably closed: literals, dangling refs and unknown
properties are compile errors, not warnings."""

from __future__ import annotations

import pytest

from conftest import patch_json
from ds_compiler import SpecValidationError, load_and_validate


def _expect_failure(spec_root) -> SpecValidationError:
    with pytest.raises(SpecValidationError) as excinfo:
        load_and_validate([spec_root])
    return excinfo.value


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #
def test_core_spec_validates(validated):
    assert {component.name for component in validated.components} == {"button", "tag", "alert", "card"}
    assert len(validated.tokens) > 50
    assert validated.overrides == ()


def test_levels_and_composition(validated):
    by_name = validated.by_name
    assert by_name["button"].level == "atom"
    assert by_name["card"].level == "molecule"
    assert by_name["card"].composition == ("button",)
    assert by_name["card"].slots == ("heading", "default")
    assert by_name["card"].block is True
    assert by_name["button"].block is False


def test_token_aliases_resolve_to_literals(validated):
    primary = validated.tokens.get("color.action.primary")
    assert primary.alias == "color.base.blue.600"
    assert validated.tokens.resolve("color.action.primary").value == "#1d4ed8"


# --------------------------------------------------------------------------- #
# Closed-value enforcement
# --------------------------------------------------------------------------- #
def test_raw_hex_value_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["modifiers"][0]["styles"]["background-color"] = "#ff0000"

    patch_json(spec_root / "components" / "button.json", mutate)
    error = _expect_failure(spec_root)
    assert "css-raw-literal" in error.codes
    offender = next(item for item in error.errors if item.code == "css-raw-literal")
    assert "#ff0000" in offender.message
    assert "button.json" in offender.location
    assert "background-color" in offender.location


def test_raw_dimension_value_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["styles"]["gap"] = "12px"

    patch_json(spec_root / "components" / "button.json", mutate)
    error = _expect_failure(spec_root)
    assert "css-raw-literal" in error.codes


def test_unknown_css_property_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["styles"]["backdrop-filter"] = "{color.action.primary}"

    patch_json(spec_root / "components" / "tag.json", mutate)
    error = _expect_failure(spec_root)
    assert "css-unknown-property" in error.codes


def test_token_type_mismatch_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["styles"]["gap"] = "{color.action.primary}"

    patch_json(spec_root / "components" / "tag.json", mutate)
    error = _expect_failure(spec_root)
    assert "css-token-type-mismatch" in error.codes


def test_keyword_only_property_rejects_token(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["styles"]["display"] = "{size.spacing.md}"

    patch_json(spec_root / "components" / "tag.json", mutate)
    error = _expect_failure(spec_root)
    assert "css-token-not-allowed" in error.codes


def test_unknown_keyword_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["styles"]["display"] = "table-cell"

    patch_json(spec_root / "components" / "tag.json", mutate)
    error = _expect_failure(spec_root)
    assert "css-raw-literal" in error.codes


# --------------------------------------------------------------------------- #
# Dangling references
# --------------------------------------------------------------------------- #
def test_dangling_token_reference_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["styles"]["gap"] = "{size.spacing.enormous}"

    patch_json(spec_root / "components" / "button.json", mutate)
    error = _expect_failure(spec_root)
    assert "css-dangling-token" in error.codes
    offender = next(item for item in error.errors if item.code == "css-dangling-token")
    assert "size.spacing.enormous" in offender.message


def test_dangling_component_reference_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["composition"] = ["hyperlink"]
        actions = data["anatomy"]["children"][2]
        actions["children"][0]["ref"] = "hyperlink"

    patch_json(spec_root / "components" / "card.json", mutate)
    error = _expect_failure(spec_root)
    assert "component-dangling-ref" in error.codes


def test_dangling_token_alias_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["color"]["action"]["primary"]["$value"] = "{color.base.blue.999}"

    patch_json(spec_root / "tokens" / "color.json", mutate)
    error = _expect_failure(spec_root)
    assert "token-alias-dangling" in error.codes


def test_token_alias_cycle_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["color"]["action"]["primary"]["$value"] = "{color.action.primary-hover}"
        data["color"]["action"]["primary-hover"]["$value"] = "{color.action.primary}"

    patch_json(spec_root / "tokens" / "color.json", mutate)
    error = _expect_failure(spec_root)
    assert "token-alias-cycle" in error.codes


# --------------------------------------------------------------------------- #
# Props, modifiers, composition contracts
# --------------------------------------------------------------------------- #
def test_unknown_property_in_component_file_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["colour"] = "blue"

    patch_json(spec_root / "components" / "tag.json", mutate)
    error = _expect_failure(spec_root)
    assert "schema-invalid" in error.codes


def test_modifier_on_undeclared_prop_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["modifiers"][0]["prop"] = "flavour"

    patch_json(spec_root / "components" / "tag.json", mutate)
    error = _expect_failure(spec_root)
    assert "modifier-unknown-prop" in error.codes


def test_modifier_value_outside_enum_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["modifiers"][0]["value"] = "chartreuse"

    patch_json(spec_root / "components" / "tag.json", mutate)
    error = _expect_failure(spec_root)
    assert "modifier-invalid-value" in error.codes


def test_composition_must_match_anatomy(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["composition"] = []

    patch_json(spec_root / "components" / "card.json", mutate)
    error = _expect_failure(spec_root)
    assert "composition-mismatch" in error.codes


def test_composed_prop_must_exist_on_target(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        actions = data["anatomy"]["children"][2]
        actions["children"][0]["props"]["shout"] = True

    patch_json(spec_root / "components" / "card.json", mutate)
    error = _expect_failure(spec_root)
    assert "component-prop-unknown" in error.codes


def test_composed_static_prop_value_checked_at_compile_time(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        actions = data["anatomy"]["children"][2]
        actions["children"][0]["props"]["variant"] = "tertiary"

    patch_json(spec_root / "components" / "card.json", mutate)
    error = _expect_failure(spec_root)
    assert "component-prop-invalid" in error.codes


def test_condition_on_undeclared_prop_fails(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["children"][2]["when"] = {"prop": "ghost", "truthy": True}

    patch_json(spec_root / "components" / "card.json", mutate)
    error = _expect_failure(spec_root)
    assert "condition-unknown-prop" in error.codes


def test_text_node_prop_must_exist(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["children"][0]["prop"] = "caption"

    patch_json(spec_root / "components" / "tag.json", mutate)
    error = _expect_failure(spec_root)
    assert "text-unknown-prop" in error.codes


def test_all_errors_are_reported_at_once(spec_copy):
    spec_root = spec_copy()

    def mutate(data):
        data["anatomy"]["styles"]["gap"] = "3px"
        data["anatomy"]["styles"]["color"] = "{color.nope}"

    patch_json(spec_root / "components" / "tag.json", mutate)
    error = _expect_failure(spec_root)
    assert {"css-raw-literal", "css-dangling-token"} <= set(error.codes)
    assert error.as_dict()["error_count"] == len(error.errors)
