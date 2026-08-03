# Agent-operated design system

The source of truth is **data, not code**: a JSON spec (`spec/`) describing tokens and
components. A compiler (`ds-compile`) turns that spec into a consumable Django app.
Nobody hand-writes CSS or templates; you edit the spec and recompile.

## The Claude Code plugin

This repo doubles as the **agentic-design-system** plugin (`.claude-plugin/`,
`skills/`). The plugin teaches agents how to operate a system like this one in any
project:

- **`ds-authoring`** — day-to-day craft: authoring tokens/components in the closed
  spec, using the override escape hatch honestly, compiling, consuming `{% ds_* %}`
  tags in Django.
- **`loop-1-expand`** — the growth loop: mine override telemetry and frontend usage
  for recurring needs, promote them into the spec, retire the motivating overrides.
- **`loop-2-contract`** — the compression loop: find dead and duplicate spec nodes,
  merge/delete with atomic reference migration, prove the change output-preserving.

Projects point the skills at their layout via `ds.config.json` (spec roots, frontend
directories, compile/verify commands). The design system may be embedded in the
project (this repo's topology) or live in a separate repo that `spec.core` points at.
The lifecycle philosophy behind the loops is in `docs/loops.md`.

## Three principles

**1. Closed data spec.** Every design value in a component spec is a reference to a
token (`"{color.action.primary}"`), never a literal. Every component reference resolves
to another spec entry. Every CSS property and keyword comes from a closed vocabulary
(`spec/vocabulary/css-properties.json`). The compiler hard-fails on raw literals
(`#ff0000`, `12px`), dangling references, unknown properties, unknown props, enum
violations and composition cycles - and reports *all* of them at once with a
machine-readable `code` + `location`. Compliance is by construction: **if it compiles,
it is compliant.**

Literals are legal in exactly two places: inside token files (the boundary where the
outside world enters the system) and inside `override` nodes.

**2. Exactly one escape hatch.** The `override` node type is the only way to express
something the vocabulary cannot. It carries arbitrary CSS/attrs plus a **required
`reason`**. Overrides compile - and every one is recorded in `overrides-report.json`
(id, component, spec file, node path, selector, reason, declarations), tagged in the
markup with a loud `ds-override` class, and emitted in CSS behind a
`/* OVERRIDE <id> - <reason> */` comment. Overrides are telemetry: a queue of
vocabulary gaps for the next growth loop.

**3. Agent-operable.** One JSON file per component, stable `id`s, explicit reference
syntax, deterministic byte-identical output (no timestamps) - so machine diffing,
promotion of recurring patterns, consolidation of near-duplicate tokens and deletion of
unused nodes are all just edits to data, verified by `ds-compile --check`.

## Layout

```
spec/
  schemas/            meta-schemas: tokens, components, css vocabulary (JSON Schema 2020-12)
  vocabulary/         the closed CSS vocabulary (properties -> accepted token types + keywords)
  tokens/             W3C DTCG token files ($value/$type, aliases "{group.name}")
  components/         one file per component: button, tag, alert (atoms), card (molecule)
src/ds_compiler/      the compiler
  loader.py           read spec roots
  validate.py         JSON Schema + reference resolution + closed-value enforcement
  tokens.py           token graph, alias resolution, CSS variable naming
  emit/               css.py, templates.py, app.py
  runtime/            ds_runtime.py - copied verbatim into the generated app
  cli.py              ds-compile
tests/                pytest suite (spec, emission, rendering, overrides, CLI, demo)
demo/                 standalone rendered page + the one override example
```

Compiled output (`build/`, `demo/build/` - both gitignored, always regenerable):

```
overrides-report.json
ds/spec.py                     prop/slot metadata used by the tag layer
ds/runtime.py                  prop validation, slot machinery
ds/templatetags/ds.py          one tag per component + {% ds_slot %}
ds/templates/ds/*.html         partials generated from anatomy
ds/static/ds/tokens.css        tokens as :root custom properties (aliases stay var())
ds/static/ds/components.css    BEM-ish classes whose values are only var(--ds-*)
```

## Usage

```bash
uv sync
uv run ds-compile --check              # validate only (exit 1 + error list on failure)
uv run ds-compile --out build          # compile the core spec
uv run ds-compile --spec spec --spec demo/spec --out demo/build   # multiple spec roots
uv run ds-compile --check --json       # machine-readable result/errors
uv run pytest                          # full suite
uv run python demo/render_demo.py      # renders demo/out.html (open it in a browser)
```

In a Django project: add the generated app to `INSTALLED_APPS`, then

```django
{% load ds %}
{% ds_button variant="primary" label="Save" %}
{% ds_tag label="New" tone="info" %}
{% ds_alert variant="warning" title="Heads up" %}
  {% ds_slot "icon" %}!{% end_ds_slot %}
  Body text goes in the default slot.
{% end_ds_alert %}
{% ds_card action_label="Open" %}
  {% ds_slot "heading" %}Card title{% end_ds_slot %}
  Body text.
{% end_ds_card %}
```

Container components (those with slots) use block form; named slots are filled with
`{% ds_slot "name" %}...{% end_ds_slot %}` and anything else in the body becomes the
`default` slot. The tag layer validates props against the spec at parse time (literals,
unknown props, missing required props) and at render time (dynamic values), raising
`DsPropError`/`DsSlotError` with the declared types and enum values in the message.

## Adding a component

1. Create `spec/components/<name>.json`:
   - `id` (`cmp.<name>`, stable forever), `name`, `level` (atom/molecule/organism)
   - `props`: typed; `enum` props list their `values`; `required` or `default`
   - `anatomy`: element tree. Each element may carry `part` (BEM element), `attrs`,
     `styles` (token references only), `states` (`hover`, `focus-visible`, `active`,
     `disabled`), `modifiers` (prop-keyed variation -> `.ds-x--y` class on the root),
     `when` (conditional part, keyed on a prop or on whether a slot is filled), and
     children: `element`, `text` (bound to a prop), `slot`, `component` (composition),
     `override`.
   - `composition`: the component names referenced in anatomy - must match exactly.
2. `uv run ds-compile --check` and fix what it reports.
3. `uv run ds-compile --out build`. You now have `{% ds_<name> %}`, a partial template
   and CSS classes.

Need a value the vocabulary lacks? Prefer **adding a token** (or a property/keyword to
`spec/vocabulary/css-properties.json`) - that grows the system for everyone. Use an
`override` node only when the thing is outside the vocabulary entirely, and write a
`reason` that says what would retire it.

## Deliberately deferred

- No composite token types (shadow, gradient, typography-as-one-token) - the demo
  override exists precisely because of this gap.
- No responsive/media-query or dark-theme layer; theming would be a second token file
  overriding the base scale.
- No icon component: `alert` has an icon slot as a placeholder.
- The growth/consolidation loops (promote recurring overrides, merge near-duplicate
  tokens, delete unused nodes) are enabled by the data model and the reports, but not
  implemented here - see `docs/loops.md` for the intended processes.
