---
name: ds-authoring
description: Work with the agent-operated JSON design system - author tokens and components in the closed spec, use the override escape hatch correctly, compile with ds-compile, and consume components in Django templates via {% ds_* %} tags. Use this whenever the task touches spec/*.json files (tokens, components, css vocabulary), ds.config.json, adding or changing a design-system component or token, fixing ds-compile errors, or building Django pages with design-system components - even if the user doesn't say "design system".
---

# Authoring in the JSON design system

The source of truth is **data, not code**: a JSON spec of tokens and components,
compiled by `ds-compile` into a Django app (template tags, partials, CSS). Nobody
hand-writes CSS or templates; you edit the spec and recompile. Compliance is by
construction: **if it compiles, it is compliant.** Lifecycle philosophy lives in
`docs/loops.md` (in the design system's repo); this skill is the day-to-day craft.

## Locate the system

Read `ds.config.json` at the project root:

- `spec.core` — the system's own spec root (may point outside the repo when the
  design system lives in a separate checkout)
- `spec.products` — product-owned spec roots (components only this project needs)
- `frontend` — directories whose Django templates consume the system
- `commands` — `check` / `build` / `test` / `render` for this project
- `artifacts` — overrides report path, rendered pages

If the file is missing, discover: spec roots are directories containing `tokens/`
and `components/`; the one with `schemas/` is the core; frontend dirs contain
templates with `{% load ds %}`. Then **write the discovered `ds.config.json`** to
the project root — every later skill run (and the lifecycle loops) depends on it.

## The three rules that never bend

1. **Closed spec.** Every design value in a component is a token reference
   (`"{color.action.primary}"`), never a literal. Every CSS property/keyword comes
   from the closed vocabulary (`<core>/vocabulary/css-properties.json`). The
   compiler hard-fails on raw literals, dangling references, unknown properties,
   enum violations — all reported at once with machine-readable `code` + `location`.
2. **Literals live in exactly two places:** token base scales (where the outside
   world enters) and `override` nodes (the single escape hatch).
3. **Compiled output is never edited.** `build/` directories are regenerable
   artifacts. If output looks wrong, the fix is in the spec.

## Tokens

DTCG format: `$value`, `$type`, aliases as `"{group.path}"`.

- Literal values go in a **base scale** (`color.base.*`, `size.spacing.*`);
  components consume **semantic aliases** (`color.text.muted`, `color.surface.default`).
- Name by meaning, never appearance: `color.highlight.surface`, not
  `color.light-orange`. Appearance-named tokens die in the next retheme.
- New value needed? Add the base entry (if genuinely new) plus the semantic alias
  components will reference. Two semantic names may share one base token — meanings
  stay distinct even when values coincide.

## Components

One JSON file per component in the owning spec root (`components/<name>.json`).
Product-specific components belong in that product's spec root, not the core.
Study an existing component of similar shape first (`card` for composition,
`alert` for slots + modifiers, `button` for states).

- `id`: `cmp.<name>` — stable forever, never reused.
- `level`: atom / molecule / organism, by composition depth.
- `props`: typed; `enum` props list `values`; mark `required` or give `default`.
- `anatomy`: element tree. Elements carry `part` (BEM element name), `styles`
  (token references only), `states` (`hover`, `focus-visible`, `active`,
  `disabled`), `modifiers` (prop-keyed styling → `.ds-x--y` class), `when`
  (conditional render keyed on a prop or slot-filled), and children of kind
  `element`, `text` (bound to a prop), `slot`, `component` (composition by `ref`,
  passing props as literals or `{"$prop": "..."}`), or `override`.
- `composition`: exactly the component names referenced in anatomy.

Workflow: edit spec → run the `check` command from config → fix what it reports
(trust the error codes; they name the real problem) → `build` → verify with
`render`/`test`.

## The escape hatch — use it honestly

Need something the vocabulary cannot express? Prefer, in order: a new token value;
a new property/keyword in the css vocabulary; a new prop/variant. Only when the
need is genuinely outside the vocabulary (e.g. a missing token *type*) use an
`override` node: it carries arbitrary CSS/attrs plus a **required `reason`** that
must say what would retire it. Overrides are not failures — they are the system's
telemetry, feeding the expand loop (`loop-1-expand`). What they must never be is a
way to dodge a compile error you could fix properly, and never invisible: they are
loudly reported in `overrides-report.json`, the markup, and the CSS.

## Consuming in Django

```django
{% load ds %}
{% ds_button variant="primary" label="Save" %}
{% ds_card action_label="Open" %}
  {% ds_slot "heading" %}Card title{% end_ds_slot %}
  Body text lands in the default slot.
{% end_ds_card %}
```

Components with slots use block form. The tag layer validates props against the
spec at parse and render time — `DsPropError`/`DsSlotError` messages include the
declared types and enum values; believe them.

## Topologies

- **Embedded (default):** spec lives in this repo; migrations are ordinary commits.
- **External:** `spec.core` points at a checkout of a separate design-system repo.
  You may add product components and overrides locally; changes to the core spec
  happen in that repo, and this project's overrides report is the demand signal
  you send back to it.
