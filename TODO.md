# TODO

Ordered by priority: adoption first (nothing else gets real usage without it),
then verification (before real consumers start churning), then loop tooling
(cheapens every future run). See `docs/loops.md` for the architecture these
items serve.

## 1. Adoption path — a new project can install and start using this

- [ ] Push this repo to GitHub (no remote configured yet)
- [ ] Make `ds_compiler` installable from another project (git dependency via uv;
      later a published package)
- [ ] `ds-init` scaffold (script or skill): create spec skeleton (tokens with base
      scales, schemas, vocabulary), `ds.config.json`, pyproject dependency, and a
      first compile — one command from empty Django project to `{% ds_button %}`
- [ ] Document the external topology end to end: `spec.core` pointing at a separate
      design-system checkout, consumer registry in the DS repo, overrides-report
      publish-back channel

## 2. Verification — the load-bearing asset, currently the thinnest

- [ ] `resolve-css` differ: emitted classes -> fully-resolved declarations
      (var() chains substituted), diffable before/after. Makes Loop 2's
      output-preserving proof mechanical instead of argued
- [ ] Screenshot render harness: render each component (and estate pages) in a real
      browser, pixel-diff against baseline. This is the "zero visual delta" oracle
      the whole breaking-changes-are-free regime depends on
- [ ] Estate coverage tracking: which pages/components are under the diff, which
      are not (an uncovered page is where "output-preserving" is an assumption)
- [ ] Content-variance property tests: declared invariants fuzzed with long
      strings/translations (line length, overflow) — known-oracle checks only

## 3. Loop robustness — idle behavior and untested paths

- [ ] Eval: Loop 1 with no recurring overrides — must promote nothing and say so
- [ ] Eval: Loop 2 on an already-minimal spec — must resist inventing work
- [ ] Eval: Loop 1 molecule extraction (recurring composition subtree across
      products) — only token promotion is exercised today
- [ ] Eval: separate-repo topology for both loops (documented, never tested)
- [ ] Clean-room baselines: rerun skill evals on fixtures stripped of
      README/docs/skills to measure the skills' real delta
- [ ] Eval-test the `ds-authoring` skill (never tested)
- [ ] Define hysteresis concretely (currently "~one Loop 1 cycle" with no number)

## 4. Loop telemetry tooling — stop re-deriving with grep every run

- [ ] `ds-analyze` command: usage graph (token/component reference counts across
      spec roots + frontend templates), dead-node list, resolved-value collisions,
      OKLCH ΔE near-collisions, override clustering by need
- [ ] Track the override ratio (overrides / total styled declarations) per run —
      the system-maturity scalar; loops append to a small metrics file
- [ ] Have both loop skills consume `ds-analyze` output instead of ad-hoc grep/jq

## 5. Vocabulary growth — compiler work Loop 1 cannot do itself

- [ ] Composite token types: shadow, gradient (the demo override exists because of
      this gap; retire it when these land)
- [ ] Theming: second token file overriding the base scale (dark mode as proof)
- [ ] Responsive/media-query layer
- [ ] Icon component (alert's icon slot is a placeholder)
- [ ] First behavioral component (modal or disclosure) — establishes the
      interaction-complexity cliff pattern: hand-written headless core, spec-bound
      styling on top

## 6. Loop 3 prerequisites (judgment layer — future work, see docs/loops.md)

- [ ] Declared text/surface pairings in the token spec — unlocks compile-time
      contrast checking (WCAG/APCA) immediately, Loop 3 stratum 1 later
- [ ] Harmony validators: type scale ratio, spacing scale membership, ramp
      lightness monotonicity in OKLCH (stratum 2)
- [ ] Initial design constitution: a few principles + 2-3 exemplar renders
- [ ] VLM judge panel over the screenshot harness (needs #2)

## 7. Operations

- [ ] CI: run pytest + `ds-compile --check` + plugin validate on every push
- [ ] Release automation (release-please, conventional commits drive versioning)
- [ ] Register plugin in DIG marketplace (experimental first)
- [ ] Run trigger-description optimization on all three skills
- [ ] `.claude/settings.json` marketplace config so team members get prompted
      to install
