---
name: loop-1-expand
description: Run the design system's Expand loop (Loop 1) - mine override telemetry and frontend usage for recurring needs, promote them into the spec (new tokens, vocabulary entries, component variants, or components), rewrite the motivating overrides as spec references, and verify the result compiles. Use this whenever the user says "run loop 1", "expand", "grow the system", "promote overrides", "pave the desire paths", "process the overrides report", or when overrides-report.json has accumulated entries that look like recurring gaps.
---

# Loop 1: Expand

Grow the spec from demand. Every override in the estate is a recorded gap in the
vocabulary; when the same gap appears repeatedly, promote it into the spec and retire
the overrides that motivated it. Philosophy: `docs/loops.md` in the design system's
repo. This skill is the procedure.

The prime directive is **minimum description length**: a promotion must shrink the
estate's total description — the spec entry it adds should delete more override/product
text than it costs. Never promote a one-off; a single override with a good `reason` is
the system working as designed, not a bug to fix.

## Step 0: Locate the system

Read `ds.config.json` at the project root: `spec.core` (the system's spec — may point
at a separate checkout), `spec.products` (product-owned spec roots), `frontend`
(directories whose Django templates consume the system), `commands`
(check/build/test/render), `artifacts` (overrides report path, rendered pages). If it
is missing, discover the layout (spec roots contain `tokens/` + `components/`; the
core has `schemas/`; frontend dirs have templates with `{% load ds %}`), write the
config, and note that in your report. The `ds-authoring` skill documents the format.

## Step 1: Gather telemetry

```bash
uv sync
<commands.build>        # produces a fresh overrides report
```

Read the overrides report (`artifacts.overridesReport`). Each entry carries `id`,
`component`, `spec_file`, `node_path`, `selector`, `reason`, `declarations`, `attrs`.
Record the baseline override count — your run must reduce it (or you promoted
nothing, which is a valid outcome when no pattern recurs).

Then gather the second kind of evidence from **actual usage**:

- **Recurring composition subtrees** in product spec files — the same arrangement of
  existing components/parts appearing in 2+ places. These need no override to be
  promotion candidates; they are molecule candidates born compliant.
- **Recurring arrangements in frontend templates** (`frontend` dirs): the same
  cluster of `{% ds_* %}` tags with the same props/nesting appearing across pages is
  the same signal one level up.

## Step 2: Cluster the evidence

Group overrides by what they are *for*, not by literal text. Two overrides belong to
one cluster when they express the same need: same properties with the same or
near-identical values, or `reason` fields naming the same missing capability.

A cluster is promotable when it has **2 or more independent occurrences**, or when
its `reason` explicitly names a gap the vocabulary can already almost express (e.g. a
missing token *value* of an existing type — the cheapest possible fill).

## Step 3: Choose the promotion form — smallest first

Escalate only when the smaller form cannot express the need:

1. **New token value** in an existing type (a missing spacing step, a missing tint).
   Literal values go in the base scale (`color.base.*` etc.); components consume a
   **semantic alias** named for meaning, not appearance (`color.highlight.surface`,
   never `color.orange-light`).
2. **New property or keyword** in the css vocabulary (`<core>/vocabulary/`) — grows
   what all components may express. Declare which token `$type`s the property accepts.
3. **New prop, variant (enum value + modifier), or state** on an existing component.
4. **New component** — for recurring composition subtrees. Follow the `ds-authoring`
   skill: stable `id` (`cmp.<name>`, never reused), `level` by composition depth, one
   JSON file in the owning spec root. Promote into the core spec only if 2+ products
   need it; a pattern recurring within one product belongs in that product's own
   spec root.

Some overrides exist because a whole **token type** is missing (gradients, shadows).
Promoting a new token type means touching the schema, vocabulary, and compiler; do it
only when the cluster is large enough to justify compiler work, and say so explicitly
in your report if you judge it not yet justified.

## Step 4: Implement and retire

Make the spec edits, then **rewrite every override in the cluster** as ordinary spec
references and delete the override nodes. A promotion that leaves its motivating
overrides in place has not finished. If an override carried several declarations and
only some are now expressible, shrink it: move the expressible declarations into
`styles`, keep the rump override with an updated `reason`.

## Step 5: Verify

```bash
<commands.check>        # must exit 0 - the closed spec is the law
<commands.test>         # full suite green
<commands.build>        # fresh overrides report
```

Confirm in the fresh report: count strictly below baseline, and no entry from the
promoted cluster remains. If the project has renderable pages (`commands.render`,
`artifacts.renderedPages`), render and confirm the promoted styling still produces
the intended visual result — a promotion is a refactor of *meaning into vocabulary*;
the pixels should not regress.

## Step 6: Commit and report

One commit per run, conventional format, e.g.
`feat(spec): promote highlight surface + 2xl spacing from recurring overrides`.
Never push.

Report exactly this:

```
## Loop 1 run
- Baseline overrides: N -> now: M
- Clusters found: <list with occurrence counts>
- Promoted: <spec nodes added, with form: token/vocabulary/variant/component>
- Retired: <override ids deleted>
- Skipped: <clusters left alone and why - one-offs are listed here, not fixed>
- Verification: check OK, tests OK (<count> passed)
```

## Guardrails

- Recurrence threshold: 2+. One-offs stay. Resist the urge to "clean up" a lone
  override — its visibility *is* the telemetry.
- Never introduce a literal outside token files (the compiler enforces this; do not
  fight it via overrides you author yourself).
- Name semantically. A token named for its appearance is a future Loop 2 casualty;
  a token named for its role survives retheming.
- If `spec.core` points at a separate repo checkout, core-spec promotions happen
  there (commit in that checkout); product-root promotions and override rewrites
  happen here. Same procedure, two commits, and say so in the report.
- Do not do Loop 2 work here (no merging, no deleting unused nodes) — one loop per
  run keeps every commit a single reviewable intent.
