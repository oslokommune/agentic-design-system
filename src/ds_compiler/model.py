"""In-memory model of a validated spec.

Anatomy nodes stay plain dicts on purpose: the spec is data, and keeping the node
tree as data makes the compiler (and future agent loops) trivially able to walk,
diff and rewrite it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from .tokens import TokenSet


def iter_nodes(node: dict, path: str = "anatomy") -> Iterator[tuple[str, dict]]:
    """Depth-first walk over an anatomy tree, yielding ``(json_path, node)``."""
    yield path, node
    kind = node.get("node")
    if kind in ("element", "override"):
        for index, child in enumerate(node.get("children") or []):
            yield from iter_nodes(child, f"{path}.children[{index}]")
    elif kind == "component":
        for slot_name, children in (node.get("slots") or {}).items():
            for index, child in enumerate(children or []):
                yield from iter_nodes(child, f"{path}.slots.{slot_name}[{index}]")


@dataclass(frozen=True)
class Prop:
    name: str
    type: str
    values: tuple[Any, ...] | None = None
    default: Any = None
    required: bool = False
    description: str | None = None

    def as_data(self) -> dict:
        data: dict[str, Any] = {"type": self.type}
        if self.values is not None:
            data["values"] = list(self.values)
        data["default"] = self.default
        data["required"] = self.required
        if self.description:
            data["description"] = self.description
        return data


@dataclass(frozen=True)
class OverrideRecord:
    """One use of the single escape hatch. Emitted to overrides-report.json."""

    id: str
    component: str
    component_id: str
    spec_file: str
    node_path: str
    selector: str
    css_class: str
    reason: str
    declarations: dict[str, str]
    attrs: dict[str, Any]

    def as_data(self) -> dict:
        return {
            "id": self.id,
            "component": self.component,
            "component_id": self.component_id,
            "spec_file": self.spec_file,
            "node_path": self.node_path,
            "selector": self.selector,
            "css_class": self.css_class,
            "reason": self.reason,
            "declarations": dict(self.declarations),
            "attrs": dict(self.attrs),
        }


@dataclass
class Component:
    id: str
    name: str
    level: str
    description: str
    props: dict[str, Prop]
    composition: tuple[str, ...]
    anatomy: dict
    source: str
    slots: tuple[str, ...] = ()
    modifier_classes: dict[str, tuple[str, Any]] = field(default_factory=dict)
    overrides: tuple[OverrideRecord, ...] = ()

    @property
    def block(self) -> bool:
        """Container components (those with slots) use ``{% ds_x %}...{% end_ds_x %}``."""
        return bool(self.slots)

    @property
    def css_class(self) -> str:
        return f"ds-{self.name}"

    @property
    def tag_name(self) -> str:
        return "ds_" + self.name.replace("-", "_")

    @property
    def template_name(self) -> str:
        return f"ds/{self.name}.html"

    def part_class(self, part: str | None) -> str:
        return self.css_class if not part else f"{self.css_class}__{part}"

    def modifier_class(self, name: str) -> str:
        return f"{self.css_class}--{name}"

    def nodes(self) -> Iterator[tuple[str, dict]]:
        return iter_nodes(self.anatomy)

    def as_data(self) -> dict:
        """Runtime metadata embedded in the generated Django app."""
        return {
            "id": self.id,
            "level": self.level,
            "description": self.description,
            "template": self.template_name,
            "block": self.block,
            "slots": list(self.slots),
            "composition": list(self.composition),
            "props": {name: prop.as_data() for name, prop in self.props.items()},
        }


@dataclass
class ValidatedSpec:
    tokens: TokenSet
    components: tuple[Component, ...]
    vocabulary: dict
    spec_roots: tuple[str, ...]

    @property
    def by_name(self) -> dict[str, Component]:
        return {component.name: component for component in self.components}

    @property
    def overrides(self) -> tuple[OverrideRecord, ...]:
        return tuple(
            override for component in self.components for override in component.overrides
        )
