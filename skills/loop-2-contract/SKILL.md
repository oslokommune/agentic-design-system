---
name: loop-2-contract
description: Run the design system's Contract loop (Loop 2) - scan the spec and its real usage for dead nodes (unused tokens/components), overlapping near-duplicates (tokens with identical or perceptually indistinguishable values, components with near-identical anatomy), merge or delete them, rewrite all references atomically, and prove the change was output-preserving. Use this whenever the user says "run loop 2", "contract", "consolidate", "dedupe the spec", "prune unused tokens", "shrink the system", "remove bloat", or after Loop 1 runs have accreted vocabulary.
---

# Loop 2: Contract

Compress the spec toward the minimum description of what products actually use.
Where Loop 1 reads product demand, Loop 2 reads the spec itself. Philosophy:
`docs/loops.md` in the design system's repo. This skill is the procedure.

Operating regime (load-bearing here): consumers are agent-maintained spec files and
templates, so **breaking changes are free as long as the migration is atomic** —
spec edit + every reference rewritten + verification in one commit. The contract
that must hold is **rendered output**, not names: a pure contraction proves itself
by producing the same pixels from a smaller spec.

## Step 0: Locate the system

Read `ds.config.json` at the project root: `spec.core`, `spec.products`, `frontend`,
`commands` (check/build/test/render), `artifacts`. If missing, discover the layout
(spec roots contain `tokens/` + `components/`; the core has `schemas/`; frontend
dirs have templates with `{% load ds %}`), write the config, and note that in your
report. The `ds-authoring` skill documents the format.

## Step 1: Build the usage picture

```bash
uv sync
<commands.check>        # must be green BEFORE you start
```

Then gather, mechanically (grep/jq — the reference syntax is closed, so text search
is sound). Usage means **all consumers**: every spec root AND the frontend templates.

- **Token reference counts**: every `{group.path}` occurrence across component
  files, token files (aliases), and the css vocabulary. A token referenced by
  nothing — including transitively: an alias chain nothing consumes — is dead.
- **Component usage**: `composition` arrays and `"ref"` nodes across all spec
  roots, **plus `{% ds_<name> %}` call sites in every `frontend` directory**. A
  component absent from both is dead; a component used only in templates is alive.
- **Value collisions**: resolve every token to its final value; group by resolved
  value. For colors, also flag *near*-collisions (perceptually indistinguishable
  pairs — OKLCH ΔE below ~0.02, or identical hex, is "the same color").
- **Anatomy overlap**: component pairs whose anatomy trees differ only in naming
  or a value or two.

## Step 2: Decide — the merge key is meaning, never appearance

Classify each candidate before touching anything:

- **Dead node** (zero references anywhere) → delete. Exception: base scales are the
  palette — an unused base *step* may stay when it is part of a deliberate scale;
  an unused *semantic alias* or component has no such excuse.
- **Same value, same meaning** (two aliases both meaning "muted surface") → merge:
  keep the better-named one, rewrite references, delete the other.
- **Same value, different meaning** (`color.danger.default` vs `color.brand.accent`
  resolving to the same red) → **do not merge the semantic names.** Point both at
  one shared base token so the literal is stored once; keep both names. Merging
  meanings welds them together; the next redesign would have to cut them apart.
- **Near-identical components** → merge only when they are one concept (one would
  be a variant/prop of the other). Similar-looking components answering different
  needs stay separate.

When unsure whether two names carry one meaning, leave them and list the pair in
the report — a wrong merge costs a redesign later; a deferred merge costs nothing.

## Step 3: Execute atomically

For each accepted merge/delete: edit the spec **and** rewrite every reference —
across all spec roots and all frontend templates — in the same change set. Grep for
the exact token path / component name afterwards: zero hits outside the definition
you kept. The estate must never be half-migrated; the `check` command on the final
state is the referee.

## Step 4: Prove it was output-preserving

Capture before starting; compare after finishing:

```bash
# BEFORE any edit:
<commands.build with --out <scratch>/before>
<commands.render>; copy artifacts.renderedPages to <scratch>/before-pages/
# AFTER all edits:
<commands.build with --out <scratch>/after>
<commands.render>; copy artifacts.renderedPages to <scratch>/after-pages/
```

- Diff the rendered pages — markup should be identical unless a merged name leaks
  into a class name; explain any diff line.
- CSS will differ where variable *names* changed; what must not change is the
  **resolved value** each declaration reaches. Spot-check merged declarations by
  resolving the var() chain in the emitted `tokens.css`.
- Run `<commands.test>` — green. Some tests name spec nodes; a test referencing a
  node you deleted is a *consumer* — migrate it in the same commit (that is
  atomicity, not test-fudging; changing an assertion's expected *value* to hide a
  visual change is fudging).

A deletion of a genuinely dead node changes no output by definition — the
before/after diff is still the proof.

## Step 5: Commit and report

One commit, conventional format, e.g.
`refactor(spec): merge duplicate muted-surface tokens, drop 3 dead nodes`. Never push.

```
## Loop 2 run
- Dead nodes deleted: <list>
- Merged: <kept <- removed, with the meaning-test reasoning>
- Re-aliased (same value, distinct meanings kept): <list>
- Deferred: <candidate pairs left alone and why>
- References rewritten: <count, across which files>
- Output-preserving proof: rendered diff <clean/explained>, resolved values checked
- Verification: check OK, tests OK (<count> passed)
- Spec size: <files/lines or node count> before -> after
```

## Guardrails

- Green before you start. Contraction on a broken estate destroys the proof.
- Hysteresis: do not delete nodes younger than ~one Loop 1 cycle (check `git log`
  on the spec file) — quick to grow, slower to prune, or borderline nodes flap.
- Never merge across semantic categories to save a token; store the value once at
  the base layer instead. Base-layer dedup is always safe; semantic-layer merges
  need the meaning test.
- Product specs and frontend templates are consumers, not your property: rewrite
  their references during migration, but do not "simplify" their design while you
  are in there.
- If `spec.core` points at a separate repo checkout, core-spec edits happen there
  and consumer rewrites here — one commit each, executed together, and the report
  must say the wave is only atomic once both land.
- Do not do Loop 1 work here (no promotions) — one loop per run, one intent per
  commit.
