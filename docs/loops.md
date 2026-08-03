# The Three Loops

How this design system evolves. The system's source of truth is a closed declarative
spec (design tokens + component composition data) compiled into consumable artifacts.
Products are expressible only as spec references plus explicitly marked **override
nodes** — the single escape hatch, always visible, always enumerable. The loops are
the processes, run by agents, that evolve the spec over time.

## Operating regime

These assumptions shape every loop and differ deliberately from human-consumed
design systems:

- **Agent-only consumers.** No human ever writes against the compiled API by hand.
  Every call site can be mechanically rewritten, so breaking changes are cheap and
  versioning ceremony (deprecation periods, `superseded-by` grace) is unnecessary.
  Changes ship as **atomic migrations**: spec change + codemod across all consumers
  + verification in one operation. The estate is never half-migrated.
- **The contract is rendered output, not API stability.** End users see the products,
  so the invariant that matters is what reaches their eyes. All change divides into:
  - *Output-preserving* (renames, merges, decompositions, refactors) — unlimited and
    free, proven by a zero-delta visual regression run across the estate.
  - *Output-changing* (actual design changes) — allowed, but requires intent. The
    pixel diff is what forces every change into one category; nothing can be both
    silently.
- **Bloat is loathed.** The ideal system is the *minimum description length* encoding
  of the estate's visual language: the shortest spec that generates the products.
  Redundancy in the encoding is the enemy; the loops are compression passes.
- **The load-bearing asset is verification coverage.** You may change anything as
  fast as you can re-verify everything. A page outside the visual regression suite is
  a page where "output-preserving" is an assumption, not a proof.

## Force model

Two forces act on the spec graph:

- **Demand grows it.** A node exists because products use it, for no other reason.
- **Coherence shrinks it.** Three triggers, one outcome: *disuse* (no consumer
  edges → delete), *overlap* (two nodes, one job → merge), *incompatibility* (used
  and unique, but foreign to the design language → rework or remove).

Size is set by demand; shape is set by identity. Maintenance churn is explicitly
**not** a force: restructuring is agent labor verified by rendering diffs, so it is
never rationed and never needs to drive decisions.

---

## Loop 1: Expand

Accretion from demand. Nothing exists speculatively; every node is earned by usage.

1. A concrete need arises in a real product and nothing in the spec covers it.
2. The smallest thing that fills the gap is built — bound to tokens, composed from
   what already exists below it.
3. The new piece enters the vocabulary and gets used.
4. Usage produces recurring combinations — the same nodes keep appearing together
   in the same arrangement.
5. Recurrence is the promotion signal: the combination is named, hardened, and
   shipped as a spec node one level up. Return to 1, one level higher.

### Two channels of newness

- **Recombination — born compliant.** New arrangements of existing vocabulary need
  no escape hatch: a spec entry that only references existing nodes is legal by
  construction the day it is written. The grammar already contains every sentence
  not yet spoken. Most "new" components are this (empirically: extracted, not
  invented).
- **Genuine novelty — born as deviation.** A need the vocabulary cannot express
  enters through an override node: visible, reasoned, logged. If it recurs, Loop 1
  promotes it into the spec and rewrites the overrides as references. If not, it
  dies as a one-off. The override channel is the system's germline — the only path
  for new genetic material — which is why it must exist and must be loud.

### Properties

- Every component is earned; the spec is a compression of observed usage.
- Each level's vocabulary becomes the next level's alphabet (atoms → molecules →
  organisms). Promotions compound: each one makes future construction cheaper.
- Simple-before-complex ordering falls out naturally: a component is only
  attemptable once its primitives exist.
- Bootstrap is just Loop 1 from an empty spec: at genesis everything is override,
  and the **override ratio** falls as the vocabulary grows to fit its products.
  That ratio is the single scalar for system maturity.

### Signals (deterministic, queryable)

- Override telemetry: `overrides-report.json` — recurrence of similar overrides is
  the promotion queue.
- Frequent-subgraph detection over product usage: recurring component combinations
  are molecule candidates.

## Loop 2: Contract

Compression. Reads the spec itself (where Loop 1 reads product usage) and shrinks
it toward the minimal encoding.

1. Scan for shrink triggers:
   - **Disuse** — nodes with no consumer edges (dead code elimination).
   - **Overlap** — near-identical nodes: token values within perceptual distance
     (ΔE in OKLCH), components with high structural overlap in anatomy/props
     (deduplication).
   - **Incompatibility** — nodes foreign to the design language (see Loop 3; until
     Loop 3 exists, this trigger is limited to structural checks: off-scale values,
     anatomy that contradicts system conventions).
2. Decide merge/delete. **The merge key is meaning, not appearance**: two tokens
   merge when their difference carries no meaning; perceptually identical values
   with distinct semantics (`color.danger` vs `color.brand-accent`) must never
   merge — the next redesign would weld them apart. Raw values may collapse freely
   *underneath* stable semantic names.
3. Execute as an atomic migration: spec change + rewrite of all call sites.
4. Verify: output-preserving transforms must show zero visual delta across the
   estate. That diff *is* the proof the change was a true refactor.
5. Return to 1.

### Properties

- Deletion is real deletion. No supersession edges, no dictionary of retired names —
  those were amortization schemes for human migration labor that agents don't need.
- Near-symmetric hysteresis with Loop 1: quick to grow, almost as quick to prune.
  (Human-consumed systems must be slow to prune; this one need not.) Keep thresholds
  slightly asymmetric to prevent borderline nodes flapping.
- Empirical warning from human-run systems (Punkt, 5 years of history): without
  this loop, systems only accrete — zero conceptual merges, zero removals,
  superseded components abandoned in place. Loop 2 is the metabolism they couldn't
  afford; its economics only work because agents pay the migration labor.

### Signals (deterministic, queryable)

- Usage counts / consumer-edge degree per node, over time.
- Pairwise perceptual distance across token values.
- Structural similarity across component anatomies and prop shapes.

## Loop 3: Judge — *future work*

Design judgment: the standard that "incompatibility" is measured against, and the
one thing demand data can never supply. Usage tells you what is *needed*, never
what is *good*. Loops 1 and 2 alone converge on coherent sediment at best.

Deferred, but the shape is settled:

### Judgment decomposes into three strata by verifiability

1. **Perceptual law — deterministic, belongs in the compiler.** Contrast (WCAG/APCA),
   touch-target minima, line-length bounds, focus visibility, color-blind
   distinguishability, perceptual spacing of palette steps. Physiology, not opinion.
   These become compile errors, enabled by declared pairings in the spec: text
   tokens defined relative to surfaces, so every text/background pair is enumerable
   and an unreadable combination is unrepresentable rather than caught.
2. **Internal harmony — consistency validators.** Not "is it beautiful" but "is it a
   system": type sizes on one ratio, spacing on one geometric scale, color ramps
   sharing a lightness curve in OKLCH, coherent chroma across hues. Harmony is
   largely relational, and relations over spec data are checkable.
3. **Taste — irreducibly judgmental.** Hierarchy, balance, density, brand fit.
   Mechanism: a panel of VLM judges with distinct lenses, majority-aggregated,
   critiquing rendered output against an explicit **design constitution** — a
   versioned artifact containing principles in prose (judge prompts), derived hard
   thresholds (strata 1–2 law), and canonical exemplars (few-shot anchors).
   Verdicts land as structured findings that gate Loop 1 promotions and feed
   Loop 2's incompatibility trigger.

### Design constraints learned the hard way

- **Verify upstream of rendering.** Post-hoc mechanistic verification of rendered
  output fails because rendering erases intent: adjacency inference on pixels is
  geometrically hard, and "uncommon = likely unintended" is falsified by design
  itself — emphasis is deliberately rare, so frequency-based detectors flag the
  designer's most intentional choices while systematic errors sail through as
  common. The closed spec preserves intent (references name their meaning;
  overrides declare their deviation), turning detection into lookup.
- **Content is the wildcard the spec can't close over.** Translations of different
  lengths, user images behind text, data-driven density. Render-time checks remain
  for these, but as *property tests of declared invariants under content variation*
  (known oracle), never open-ended anomaly hunting.
- **Shrink stratum 3, don't mechanize it.** When a judge critique recurs, ask
  whether it can be reformulated as a relation over spec data; if so it graduates
  into stratum 2 and becomes a validator. The constitution's law section grows the
  way the component vocabulary does: by promoting recurring judgments.
- **Frequency heuristics are prioritization, not correctness.** "Uncommon" means
  "look here first," never "probably wrong." Rankings tolerate false positives;
  verdicts don't.
- **The human's seat.** Loop 3 is where human taste enters the otherwise agent-run
  system: curating the constitution, choosing exemplars, adjudicating judge splits.
  Not reviewing buttons — holding the ought.

### Prerequisites before starting Loop 3

- Visual regression coverage across the estate (also required by Loop 2 — build once).
- Declared surface/text pairings in the token spec (unlocks stratum 1 in the compiler).
- An initial design constitution, however small: a few principles and 2–3 exemplars.

---

## Summary

| | Loop 1: Expand | Loop 2: Contract | Loop 3: Judge *(future)* |
|---|---|---|---|
| Reads | Product usage + override telemetry | The spec itself | Rendered output vs the constitution |
| Asks | What recurs and deserves a name? | What is dead, duplicate, or foreign? | Is this vocabulary one language, and is it good? |
| Acts by | Promotion into the spec | Merge / delete via atomic migration | Findings that gate Loop 1 and trigger Loop 2 |
| Verified by | Compiles; references resolve | Zero visual delta across the estate | Strata 1–2: validators; stratum 3: judge panel + human appeal |
| Nature | Empirical (demand) | Empirical (redundancy) | Normative (identity) |
