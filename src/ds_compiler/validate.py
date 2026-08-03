"""Step 1 of compilation: make the spec provably compilable.

Three layers, all hard failures:

1. JSON Schema  - shape of token files, component files and the CSS vocabulary.
2. Reference resolution - token aliases, token references in styles, component
   references in anatomy, prop references in composed props.
3. Closed-value enforcement - a style value is either a token reference of an
   accepted ``$type`` or an enumerated keyword. Literals (``#fff``, ``12px``,
   ``1rem``) are only legal inside token files and inside ``override`` nodes.
"""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from .errors import SpecError, SpecValidationError
from .loader import RawSpec, SpecFile
from .model import Component, OverrideRecord, Prop, ValidatedSpec, iter_nodes
from .tokens import ALIAS_RE, TokenSet, build_token_set, effective_type

RESERVED_PROP_NAMES = frozenset({"slots"})


# --------------------------------------------------------------------------- #
# JSON Schema layer
# --------------------------------------------------------------------------- #
def _pointer(error) -> str:
    return "/" + "/".join(str(part) for part in error.absolute_path)


def _refine(error):
    """Descend into anyOf/oneOf sub-errors so the message names the real problem."""
    while error.context:
        candidate = best_match(error.context)
        if candidate is None:
            break
        error = candidate
    return error


def _schema_validate(raw: RawSpec, errors: list[SpecError]) -> None:
    pairs: list[tuple[str, list[SpecFile]]] = [
        ("tokens.schema.json", raw.token_files),
        ("component.schema.json", raw.component_files),
        ("css-vocabulary.schema.json", raw.vocabulary_files),
    ]
    for schema_name, files in pairs:
        schema = raw.schemas[schema_name]
        validator = Draft202012Validator(schema)
        for spec_file in files:
            found = sorted(validator.iter_errors(spec_file.data), key=lambda e: list(e.absolute_path))
            for error in found:
                refined = _refine(error)
                errors.append(
                    SpecError(
                        "schema-invalid",
                        f"{spec_file.location}#{_pointer(refined)}",
                        f"{refined.message} (schema: {schema_name})",
                    )
                )


# --------------------------------------------------------------------------- #
# Prop helpers
# --------------------------------------------------------------------------- #
def _value_matches(prop: Prop, value: Any) -> bool:
    if prop.type == "enum":
        return value in (prop.values or ())
    if prop.type == "boolean":
        return isinstance(value, bool)
    if prop.type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if prop.type == "string":
        return isinstance(value, str)
    return False  # pragma: no cover - schema restricts type


def _describe(prop: Prop) -> str:
    if prop.type == "enum":
        return f"enum{list(prop.values or ())}"
    return prop.type


# --------------------------------------------------------------------------- #
# Closed-value enforcement
# --------------------------------------------------------------------------- #
def _check_styles(
    styles: dict[str, Any],
    location: str,
    vocabulary: dict,
    tokens: TokenSet,
    errors: list[SpecError],
) -> None:
    properties = vocabulary["properties"]
    for name, raw_value in styles.items():
        spec = properties.get(name)
        if spec is None:
            errors.append(
                SpecError(
                    "css-unknown-property",
                    f"{location}.{name}",
                    f"CSS property '{name}' is not in the closed vocabulary; "
                    "add it to vocabulary/css-properties.json to make it usable",
                )
            )
            continue
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        if len(values) > 1 and not spec.get("multi"):
            errors.append(
                SpecError(
                    "css-multi-not-allowed",
                    f"{location}.{name}",
                    f"CSS property '{name}' does not accept a list of values",
                )
            )
        token_types = tuple(spec.get("token_types") or ())
        keywords = tuple(spec.get("keywords") or ())
        for value in values:
            match = ALIAS_RE.match(value)
            if match:
                ref = match.group(1)
                if not token_types:
                    errors.append(
                        SpecError(
                            "css-token-not-allowed",
                            f"{location}.{name}",
                            f"CSS property '{name}' takes keywords only ({list(keywords)}), not token reference '{ref}'",
                        )
                    )
                    continue
                token = tokens.get(ref)
                if token is None:
                    errors.append(
                        SpecError(
                            "css-dangling-token",
                            f"{location}.{name}",
                            f"token reference '{{{ref}}}' does not resolve to any token",
                        )
                    )
                    continue
                token_type = effective_type(tokens, token)
                if token_type not in token_types:
                    errors.append(
                        SpecError(
                            "css-token-type-mismatch",
                            f"{location}.{name}",
                            f"token '{ref}' is $type '{token_type}' but '{name}' accepts {list(token_types)}",
                        )
                    )
                continue
            if value.startswith("{") or value.endswith("}"):
                errors.append(
                    SpecError(
                        "css-malformed-reference",
                        f"{location}.{name}",
                        f"{value!r} looks like a token reference but is malformed; expected '{{group.name}}'",
                    )
                )
                continue
            if value in keywords:
                continue
            errors.append(
                SpecError(
                    "css-raw-literal",
                    f"{location}.{name}",
                    f"raw value {value!r} is not allowed: '{name}' accepts token references of type "
                    f"{list(token_types)} or the keywords {list(keywords)}. "
                    "Add a token (or an `override` node with a reason) instead of a literal",
                )
            )


def _check_states(
    states: dict[str, Any],
    location: str,
    vocabulary: dict,
    tokens: TokenSet,
    errors: list[SpecError],
) -> None:
    allowed = tuple(vocabulary.get("states") or ())
    for state, body in states.items():
        if state not in allowed:
            errors.append(
                SpecError(
                    "css-unknown-state",
                    f"{location}.states.{state}",
                    f"state '{state}' is not in the closed vocabulary {list(allowed)}",
                )
            )
            continue
        _check_styles(body.get("styles") or {}, f"{location}.states.{state}.styles", vocabulary, tokens, errors)


# --------------------------------------------------------------------------- #
# Component construction
# --------------------------------------------------------------------------- #
def _build_component(spec_file: SpecFile) -> Component:
    data = spec_file.data
    props: dict[str, Prop] = {}
    for name, raw in (data.get("props") or {}).items():
        props[name] = Prop(
            name=name,
            type=raw["type"],
            values=tuple(raw["values"]) if "values" in raw else None,
            default=raw.get("default"),
            required=bool(raw.get("required", False)),
            description=raw.get("description"),
        )
    return Component(
        id=data["id"],
        name=data["name"],
        level=data["level"],
        description=data.get("description", ""),
        props=props,
        composition=tuple(data.get("composition") or []),
        anatomy=data["anatomy"],
        source=spec_file.location,
    )


def _check_condition(
    component: Component,
    condition: dict,
    location: str,
    slots: tuple[str, ...],
    errors: list[SpecError],
) -> None:
    if "slot" in condition:
        if condition["slot"] not in slots:
            errors.append(
                SpecError(
                    "condition-unknown-slot",
                    location,
                    f"condition references slot '{condition['slot']}' which '{component.name}' does not declare "
                    f"(declared: {list(slots)})",
                )
            )
        return
    prop_name = condition["prop"]
    prop = component.props.get(prop_name)
    if prop is None:
        errors.append(
            SpecError(
                "condition-unknown-prop",
                location,
                f"condition references undeclared prop '{prop_name}' (declared: {sorted(component.props)})",
            )
        )
        return
    if "value" in condition and not _value_matches(prop, condition["value"]):
        errors.append(
            SpecError(
                "condition-invalid-value",
                location,
                f"condition value {condition['value']!r} is not valid for prop '{prop_name}' ({_describe(prop)})",
            )
        )


def _check_attrs(component: Component, attrs: dict, location: str, errors: list[SpecError]) -> None:
    for name, value in attrs.items():
        if not isinstance(value, dict):
            continue
        prop_name = value.get("$prop") or value.get("$flag")
        prop = component.props.get(prop_name)
        if prop is None:
            errors.append(
                SpecError(
                    "attr-unknown-prop",
                    f"{location}.attrs.{name}",
                    f"attribute binds to undeclared prop '{prop_name}' (declared: {sorted(component.props)})",
                )
            )
            continue
        if "$flag" in value and prop.type != "boolean":
            errors.append(
                SpecError(
                    "attr-flag-not-boolean",
                    f"{location}.attrs.{name}",
                    f"$flag attributes require a boolean prop; '{prop_name}' is {_describe(prop)}",
                )
            )


def _validate_component(
    component: Component,
    by_name: dict[str, Component],
    tokens: TokenSet,
    vocabulary: dict,
    override_ids: dict[str, str],
    errors: list[SpecError],
) -> None:
    source = component.source

    for name, prop in component.props.items():
        location = f"{source}#/props/{name}"
        if name in RESERVED_PROP_NAMES:
            errors.append(
                SpecError("prop-reserved-name", location, f"prop name '{name}' is reserved by the runtime")
            )
        if prop.required and prop.default is not None:
            errors.append(
                SpecError("prop-required-with-default", location, "a required prop must not declare a default")
            )
        if prop.default is not None and not _value_matches(prop, prop.default):
            errors.append(
                SpecError(
                    "prop-invalid-default",
                    location,
                    f"default {prop.default!r} is not valid for {_describe(prop)}",
                )
            )

    # First pass: collect slots and parts so conditions can be checked against them.
    slots: list[str] = []
    parts: dict[str, str] = {}
    for path, node in component.nodes():
        kind = node.get("node")
        if kind == "slot":
            if node["name"] in slots:
                errors.append(
                    SpecError(
                        "slot-duplicate",
                        f"{source}#/{path}",
                        f"slot '{node['name']}' is declared more than once in '{component.name}'",
                    )
                )
            else:
                slots.append(node["name"])
        part = node.get("part")
        if part:
            if part in parts:
                errors.append(
                    SpecError(
                        "part-duplicate",
                        f"{source}#/{path}",
                        f"part '{part}' is already used at {parts[part]}; parts must be unique per component",
                    )
                )
            else:
                parts[part] = path
    component.slots = tuple(slots)

    modifier_classes: dict[str, tuple[str, Any]] = {}
    overrides: list[OverrideRecord] = []
    referenced: list[str] = []

    for path, node in component.nodes():
        location = f"{source}#/{path}"
        kind = node.get("node")

        if "when" in node:
            _check_condition(component, node["when"], f"{location}.when", component.slots, errors)

        if kind == "element":
            _check_attrs(component, node.get("attrs") or {}, location, errors)
            _check_styles(node.get("styles") or {}, f"{location}.styles", vocabulary, tokens, errors)
            _check_states(node.get("states") or {}, location, vocabulary, tokens, errors)
            for index, modifier in enumerate(node.get("modifiers") or []):
                mod_location = f"{location}.modifiers[{index}]"
                prop_name = modifier["prop"]
                prop = component.props.get(prop_name)
                if prop is None:
                    errors.append(
                        SpecError(
                            "modifier-unknown-prop",
                            mod_location,
                            f"modifier keys on undeclared prop '{prop_name}' (declared: {sorted(component.props)})",
                        )
                    )
                elif not _value_matches(prop, modifier["value"]):
                    errors.append(
                        SpecError(
                            "modifier-invalid-value",
                            mod_location,
                            f"modifier value {modifier['value']!r} is not valid for prop '{prop_name}' ({_describe(prop)})",
                        )
                    )
                class_name = modifier.get("class") or _default_modifier_class(modifier["value"])
                key = (prop_name, modifier["value"])
                existing = modifier_classes.get(class_name)
                if existing is not None and existing != key:
                    errors.append(
                        SpecError(
                            "modifier-class-conflict",
                            mod_location,
                            f"modifier class '{component.modifier_class(class_name)}' already means "
                            f"{existing[0]}={existing[1]!r}; give this modifier an explicit distinct \"class\"",
                        )
                    )
                else:
                    modifier_classes[class_name] = key
                _check_styles(modifier.get("styles") or {}, f"{mod_location}.styles", vocabulary, tokens, errors)
                _check_states(modifier.get("states") or {}, mod_location, vocabulary, tokens, errors)

        elif kind == "text":
            if "prop" in node and node["prop"] not in component.props:
                errors.append(
                    SpecError(
                        "text-unknown-prop",
                        location,
                        f"text node binds to undeclared prop '{node['prop']}' (declared: {sorted(component.props)})",
                    )
                )

        elif kind == "override":
            _check_attrs(component, node.get("attrs") or {}, location, errors)
            override_id = node["id"]
            if override_id in override_ids:
                errors.append(
                    SpecError(
                        "override-duplicate-id",
                        location,
                        f"override id '{override_id}' is already used at {override_ids[override_id]}",
                    )
                )
            else:
                override_ids[override_id] = location
            css_class = override_class(override_id)
            overrides.append(
                OverrideRecord(
                    id=override_id,
                    component=component.name,
                    component_id=component.id,
                    spec_file=source,
                    node_path=path,
                    selector=f".{css_class}",
                    css_class=css_class,
                    reason=node["reason"],
                    declarations=dict(node.get("css") or {}),
                    attrs=dict(node.get("attrs") or {}),
                )
            )

        elif kind == "component":
            ref = node["ref"]
            referenced.append(ref)
            target = by_name.get(ref)
            if target is None:
                errors.append(
                    SpecError(
                        "component-dangling-ref",
                        location,
                        f"references unknown component '{ref}' (known: {sorted(by_name)})",
                    )
                )
                continue
            if target.name == component.name:
                errors.append(
                    SpecError("composition-self-reference", location, f"'{component.name}' composes itself")
                )
            _check_composed_props(component, target, node, location, errors)
            provided_slots = node.get("slots") or {}
            for slot_name in provided_slots:
                if slot_name not in target.slots:
                    errors.append(
                        SpecError(
                            "component-slot-unknown",
                            f"{location}.slots.{slot_name}",
                            f"'{ref}' has no slot '{slot_name}' (declared: {list(target.slots)})",
                        )
                    )
            if target.block and not provided_slots:
                errors.append(
                    SpecError(
                        "component-slots-required",
                        location,
                        f"'{ref}' is a container component; provide content for at least one of its slots "
                        f"{list(target.slots)} via \"slots\"",
                    )
                )
            if provided_slots and not target.block:
                errors.append(
                    SpecError(
                        "component-slots-unexpected",
                        location,
                        f"'{ref}' declares no slots, so \"slots\" cannot be used",
                    )
                )

    component.modifier_classes = modifier_classes
    component.overrides = tuple(overrides)

    declared_composition = set(component.composition)
    actual_composition = set(referenced)
    if declared_composition != actual_composition:
        errors.append(
            SpecError(
                "composition-mismatch",
                f"{source}#/composition",
                f"declared composition {sorted(declared_composition)} does not match the component "
                f"references found in anatomy {sorted(actual_composition)}",
            )
        )


def _check_composed_props(
    parent: Component,
    target: Component,
    node: dict,
    location: str,
    errors: list[SpecError],
) -> None:
    provided = node.get("props") or {}
    for name, value in provided.items():
        prop = target.props.get(name)
        if prop is None:
            errors.append(
                SpecError(
                    "component-prop-unknown",
                    f"{location}.props.{name}",
                    f"'{target.name}' has no prop '{name}' (declared: {sorted(target.props)})",
                )
            )
            continue
        if isinstance(value, dict):
            source_prop = parent.props.get(value["$prop"])
            if source_prop is None:
                errors.append(
                    SpecError(
                        "component-prop-ref-unknown",
                        f"{location}.props.{name}",
                        f"$prop '{value['$prop']}' is not declared on '{parent.name}' "
                        f"(declared: {sorted(parent.props)})",
                    )
                )
            elif source_prop.type != prop.type:
                errors.append(
                    SpecError(
                        "component-prop-type-mismatch",
                        f"{location}.props.{name}",
                        f"'{parent.name}.{value['$prop']}' is {_describe(source_prop)} but "
                        f"'{target.name}.{name}' is {_describe(prop)}",
                    )
                )
            elif prop.type == "enum" and not set(source_prop.values or ()) <= set(prop.values or ()):
                errors.append(
                    SpecError(
                        "component-prop-enum-widens",
                        f"{location}.props.{name}",
                        f"'{parent.name}.{value['$prop']}' allows {list(source_prop.values or ())} which is not a "
                        f"subset of '{target.name}.{name}' {list(prop.values or ())}",
                    )
                )
        elif not _value_matches(prop, value):
            errors.append(
                SpecError(
                    "component-prop-invalid",
                    f"{location}.props.{name}",
                    f"value {value!r} is not valid for '{target.name}.{name}' ({_describe(prop)})",
                )
            )
    for name, prop in target.props.items():
        if prop.required and name not in provided:
            errors.append(
                SpecError(
                    "component-prop-missing",
                    f"{location}.props",
                    f"required prop '{name}' of '{target.name}' is not provided",
                )
            )


def _default_modifier_class(value: Any) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    return str(value).lower().replace("_", "-")


def override_class(override_id: str) -> str:
    """CSS class for an override node: ``ovr.promo.gradient`` -> ``ds-o-promo-gradient``."""
    tail = override_id[4:] if override_id.startswith("ovr.") else override_id
    return "ds-o-" + tail.replace(".", "-")


def _validate_graph(components: tuple[Component, ...], errors: list[SpecError]) -> None:
    by_name: dict[str, Component] = {}
    by_id: dict[str, Component] = {}
    by_tag: dict[str, Component] = {}
    for component in components:
        if component.name in by_name:
            errors.append(
                SpecError(
                    "component-duplicate-name",
                    f"{component.source}#/name",
                    f"component name '{component.name}' is already defined in {by_name[component.name].source}",
                )
            )
        else:
            by_name[component.name] = component
        if component.id in by_id:
            errors.append(
                SpecError(
                    "component-duplicate-id",
                    f"{component.source}#/id",
                    f"component id '{component.id}' is already used by {by_id[component.id].source}",
                )
            )
        else:
            by_id[component.id] = component
        if component.tag_name in by_tag:
            errors.append(
                SpecError(
                    "component-tag-collision",
                    f"{component.source}#/name",
                    f"template tag '{component.tag_name}' collides with {by_tag[component.tag_name].name}",
                )
            )
        else:
            by_tag[component.tag_name] = component

    # Composition must be a DAG.
    state: dict[str, int] = {}

    def visit(name: str, trail: tuple[str, ...]) -> None:
        if state.get(name) == 2:
            return
        if state.get(name) == 1:
            cycle = " -> ".join(trail + (name,))
            errors.append(
                SpecError("composition-cycle", f"{by_name[name].source}#/composition", f"composition cycle: {cycle}")
            )
            return
        state[name] = 1
        for ref in by_name[name].composition:
            if ref in by_name:
                visit(ref, trail + (name,))
        state[name] = 2

    for component in components:
        if component.name in by_name:
            visit(component.name, ())


def validate_spec(raw: RawSpec) -> ValidatedSpec:
    """Validate ``raw`` completely. Raises :class:`SpecValidationError` on any problem."""
    errors: list[SpecError] = []
    _schema_validate(raw, errors)
    if errors:
        # Semantic passes assume schema-valid shapes.
        raise SpecValidationError(errors)

    tokens = build_token_set(raw.token_files, errors)
    vocabulary = raw.vocabulary
    components = tuple(_build_component(spec_file) for spec_file in raw.component_files)
    by_name = {component.name: component for component in components}
    override_ids: dict[str, str] = {}
    for component in components:
        _validate_component(component, by_name, tokens, vocabulary, override_ids, errors)
    _validate_graph(components, errors)

    if errors:
        raise SpecValidationError(sorted(errors))
    return ValidatedSpec(
        tokens=tokens,
        components=components,
        vocabulary=vocabulary,
        spec_roots=tuple(str(root) for root in raw.roots),
    )
