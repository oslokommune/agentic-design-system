# agentic-design-system

This repo is both a Claude Code plugin (`skills/`) and the reference implementation
of the design system it operates (`spec/`, `src/ds_compiler/`, `demo/`).

## Versioning

- Always bump the version in `.claude-plugin/plugin.json` after any changes, following semver:
  - `patch` for bug fixes
  - `minor` for new features or non-breaking changes
  - `major` for breaking changes

## Ground rules

- The spec is the source of truth; compiled output (`build/`, `demo/build/`) is never
  edited by hand and never committed.
- Literals live in exactly two places: token base scales and `override` nodes.
- One loop per run, one intent per commit. See `docs/loops.md`.
