"""The compiled Django app must actually render, and must refuse bad props."""

from __future__ import annotations

import re

import pytest


def strip_ws(html: str) -> str:
    return re.sub(r"\s+", " ", html).strip()


# --------------------------------------------------------------------------- #
# Atoms
# --------------------------------------------------------------------------- #
def test_button_renders_classes_and_label(render):
    html = render('{% load ds %}{% ds_button variant="primary" label="Save" %}')
    assert 'class="ds-button ds-button--primary ds-button--md"' in html
    assert '<span class="ds-button__label">Save</span>' in html
    assert 'type="button"' in html


def test_button_variant_and_size_modifiers(render):
    html = render('{% load ds %}{% ds_button variant="secondary" size="sm" label="Go" %}')
    assert "ds-button--secondary" in html
    assert "ds-button--sm" in html
    assert "ds-button--primary" not in html
    assert "ds-button--md" not in html


def test_button_boolean_flag_attribute(render):
    assert " disabled" in render('{% load ds %}{% ds_button label="No" disabled=True %}')
    assert " disabled" not in render('{% load ds %}{% ds_button label="Yes" %}')


def test_prop_defaults_come_from_the_spec(render):
    html = render('{% load ds %}{% ds_button label="Default" %}')
    assert "ds-button--primary" in html
    assert "ds-button--md" in html


def test_prop_values_are_escaped(render):
    html = render("{% load ds %}{% ds_button label=evil %}", evil="<script>x</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_tag_tones(render):
    for tone in ("neutral", "info", "success", "danger"):
        html = render('{%% load ds %%}{%% ds_tag label="L" tone="%s" %%}' % tone)
        assert f"ds-tag--{tone}" in html
        assert strip_ws(html).endswith("L</span>")


# --------------------------------------------------------------------------- #
# Slots and conditional parts
# --------------------------------------------------------------------------- #
def test_alert_slots_and_conditional_parts(render):
    html = render(
        '{% load ds %}{% ds_alert variant="danger" title="Boom" %}'
        '{% ds_slot "icon" %}!{% end_ds_slot %}It broke.{% end_ds_alert %}'
    )
    assert "ds-alert--danger" in html
    assert '<span class="ds-alert__icon">!</span>' in html
    assert '<strong class="ds-alert__title">Boom</strong>' in html
    assert "It broke." in html


def test_alert_omits_parts_when_slot_and_prop_are_empty(render):
    html = render('{% load ds %}{% ds_alert %}Just a message.{% end_ds_alert %}')
    assert "ds-alert__icon" not in html
    assert "ds-alert__title" not in html
    assert "ds-alert--info" in html  # default variant
    assert "Just a message." in html


def test_card_composes_button_by_reference(render):
    html = render(
        '{% load ds %}{% ds_card action_label="Open" action_variant="secondary" %}'
        '{% ds_slot "heading" %}Title{% end_ds_slot %}Body text{% end_ds_card %}'
    )
    assert '<h3 class="ds-card__heading">Title</h3>' in html
    assert "Body text" in html
    assert 'class="ds-card__actions"' in html
    # The composed component is rendered through its own generated template.
    assert "ds-button ds-button--secondary ds-button--md" in html
    assert "<span class=\"ds-button__label\">Open</span>" in html


def test_card_without_action_drops_the_actions_part(render):
    html = render('{% load ds %}{% ds_card %}{% ds_slot "heading" %}T{% end_ds_slot %}Body{% end_ds_card %}')
    assert "ds-card__actions" not in html
    assert "ds-button" not in html


def test_nested_container_components_keep_their_own_slots(render):
    html = render(
        "{% load ds %}"
        '{% ds_card %}{% ds_slot "heading" %}Outer{% end_ds_slot %}'
        '{% ds_card tone="muted" %}{% ds_slot "heading" %}Inner{% end_ds_slot %}Inner body{% end_ds_card %}'
        "{% end_ds_card %}"
    )
    assert '<h3 class="ds-card__heading">Outer</h3>' in html
    assert '<h3 class="ds-card__heading">Inner</h3>' in html
    assert "ds-card--muted" in html
    # Slot content is inserted as markup, not escaped text.
    assert "&lt;article" not in html
    assert html.count("<article") == 2


# --------------------------------------------------------------------------- #
# Prop validation at the tag layer
# --------------------------------------------------------------------------- #
def test_invalid_enum_value_raises(render, ds_runtime):
    with pytest.raises(ds_runtime.DsPropError) as excinfo:
        render('{% load ds %}{% ds_button label="x" variant="tertiary" %}')
    assert "variant" in str(excinfo.value)
    assert "'primary'" in str(excinfo.value)


def test_invalid_enum_value_from_context_raises_at_render_time(render, ds_runtime):
    with pytest.raises(ds_runtime.DsPropError):
        render("{% load ds %}{% ds_button label=\"x\" variant=chosen %}", chosen="tertiary")


def test_unknown_prop_raises(render, ds_runtime):
    with pytest.raises(ds_runtime.DsPropError) as excinfo:
        render('{% load ds %}{% ds_button label="x" colour="red" %}')
    assert "unknown prop 'colour'" in str(excinfo.value)


def test_missing_required_prop_raises(render, ds_runtime):
    with pytest.raises(ds_runtime.DsPropError) as excinfo:
        render('{% load ds %}{% ds_button variant="primary" %}')
    assert "required prop 'label'" in str(excinfo.value)


def test_positional_arguments_rejected(render, ds_runtime):
    with pytest.raises(ds_runtime.DsPropError):
        render('{% load ds %}{% ds_button "Save" %}')


def test_unknown_slot_raises(render, ds_runtime):
    with pytest.raises(ds_runtime.DsSlotError) as excinfo:
        render('{% load ds %}{% ds_card %}{% ds_slot "footer" %}x{% end_ds_slot %}{% end_ds_card %}')
    assert "footer" in str(excinfo.value)


def test_duplicate_slot_raises(render, ds_runtime):
    with pytest.raises(ds_runtime.DsSlotError):
        render(
            "{% load ds %}{% ds_card %}"
            '{% ds_slot "heading" %}a{% end_ds_slot %}{% ds_slot "heading" %}b{% end_ds_slot %}'
            "{% end_ds_card %}"
        )


def test_slot_outside_component_raises(render, ds_runtime):
    with pytest.raises(ds_runtime.DsSlotError):
        render('{% load ds %}{% ds_slot "heading" %}x{% end_ds_slot %}')


def test_boolean_prop_accepts_string_form(render):
    assert " disabled" in render('{% load ds %}{% ds_button label="x" disabled="true" %}')
    assert " disabled" not in render('{% load ds %}{% ds_button label="x" disabled="false" %}')
