"""Django partial template emission.

One template per component under ``templates/ds/<name>.html``. Prop-keyed
variation compiles to ``{% if %}`` guards so the template is a faithful,
human-readable projection of the anatomy tree; composition compiles to the
generated tag of the referenced component.
"""

from __future__ import annotations

from html import escape
from typing import Any

from ..model import Component
from ..validate import override_class

VOID_TAGS = frozenset({"img"})
INLINE_KINDS = frozenset({"text", "slot"})


def _condition_expr(condition: dict) -> str:
    if "slot" in condition:
        return f"slots.{condition['slot']}"
    prop = condition["prop"]
    if condition.get("truthy"):
        return prop
    value = condition["value"]
    if value is True:
        return prop
    if value is False:
        return f"not {prop}"
    if isinstance(value, (int, float)):
        return f"{prop} == {value}"
    return f"{prop} == '{value}'"


def _attr_fragment(name: str, value: Any) -> str:
    if isinstance(value, dict):
        if "$flag" in value:
            return "{%% if %s %%} %s{%% endif %%}" % (value["$flag"], name)
        prop = value["$prop"]
        return '{%% if %s %%} %s="{{ %s }}"{%% endif %%}' % (prop, name, prop)
    if value is True:
        return f" {name}"
    if value is False:
        return ""
    return f' {name}="{escape(str(value), quote=True)}"'


def _root_class_attr(component: Component) -> str:
    fragments = [component.css_class]
    for class_name, (prop, value) in component.modifier_classes.items():
        condition = _condition_expr({"prop": prop, "value": value})
        fragments.append(
            "{%% if %s %%} %s{%% endif %%}" % (condition, component.modifier_class(class_name))
        )
    return ' class="' + fragments[0] + "".join(fragments[1:]) + '"'


def _class_attr(component: Component, node: dict, is_root: bool) -> str:
    if is_root:
        return _root_class_attr(component)
    classes: list[str] = []
    part = node.get("part")
    if part:
        classes.append(component.part_class(part))
    if node.get("node") == "override":
        classes.extend(["ds-override", override_class(node["id"])])
    if not classes:
        return ""
    return ' class="' + " ".join(classes) + '"'


def _tag_kwarg_value(value: Any) -> str:
    if isinstance(value, dict):
        return value["$prop"]
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return str(value)
    return '"%s"' % str(value).replace('"', "&quot;")


def _render_component_ref(node: dict, component: Component, by_name: dict[str, Component], indent: str) -> list[str]:
    target = by_name[node["ref"]]
    kwargs = " ".join(
        f"{name}={_tag_kwarg_value(value)}" for name, value in (node.get("props") or {}).items()
    )
    open_tag = f"{{% {target.tag_name}{' ' + kwargs if kwargs else ''} %}}"
    slots = node.get("slots") or {}
    if not slots:
        return [indent + open_tag]
    lines = [indent + open_tag]
    for slot_name, children in slots.items():
        lines.append(f'{indent}  {{% ds_slot "{slot_name}" %}}')
        for child in children or []:
            lines.extend(_render_node(child, component, by_name, indent + "    ", is_root=False))
        lines.append(f"{indent}  {{% end_ds_slot %}}")
    lines.append(f"{indent}{{% end_{target.tag_name} %}}")
    return lines


def _render_node(
    node: dict,
    component: Component,
    by_name: dict[str, Component],
    indent: str,
    is_root: bool,
) -> list[str]:
    kind = node["node"]

    if kind == "text":
        content = "{{ %s }}" % node["prop"] if "prop" in node else escape(node["literal"])
        lines = [indent + content]
    elif kind == "slot":
        lines = [indent + "{{ slots.%s }}" % node["name"]]
    elif kind == "component":
        lines = _render_component_ref(node, component, by_name, indent)
    else:  # element / override
        tag = node["tag"]
        attrs = _class_attr(component, node, is_root)
        attrs += "".join(_attr_fragment(name, value) for name, value in (node.get("attrs") or {}).items())
        children = node.get("children") or []
        if tag in VOID_TAGS:
            lines = [f"{indent}<{tag}{attrs} />"]
        elif not children:
            lines = [f"{indent}<{tag}{attrs}></{tag}>"]
        elif all(child["node"] in INLINE_KINDS and "when" not in child for child in children):
            inner = "".join(
                _render_node(child, component, by_name, "", is_root=False)[0] for child in children
            )
            lines = [f"{indent}<{tag}{attrs}>{inner}</{tag}>"]
        else:
            lines = [f"{indent}<{tag}{attrs}>"]
            for child in children:
                lines.extend(_render_node(child, component, by_name, indent + "  ", is_root=False))
            lines.append(f"{indent}</{tag}>")

    if "when" in node:
        expression = _condition_expr(node["when"])
        lines = [f"{indent}{{% if {expression} %}}", *lines, f"{indent}{{% endif %}}"]
    return lines


def render_template(component: Component, by_name: dict[str, Component]) -> str:
    """Render the Django partial template for ``component``."""
    header = [
        f"{{# GENERATED by ds-compile from {component.source} - do not edit. #}}",
        f"{{# component: {component.id} ({component.level}) "
        f"props: {', '.join(component.props) or 'none'} "
        f"slots: {', '.join(component.slots) or 'none'} #}}",
    ]
    if component.composition:
        header.append("{% load ds %}")
    body = _render_node(component.anatomy, component, by_name, "", is_root=True)
    return "\n".join(header + body) + "\n"
