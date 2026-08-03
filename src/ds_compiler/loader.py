"""Step 0: read the spec tree off disk.

A spec root is a directory laid out as::

    <root>/tokens/*.json          W3C DTCG token files
    <root>/components/*.json      one component per file
    <root>/vocabulary/*.json      closed CSS vocabulary (optional in secondary roots)
    <root>/schemas/*.json         meta-schemas (optional in secondary roots)

Multiple roots may be given; later roots extend earlier ones (this is how the demo
adds a component without touching the core spec).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .errors import SpecError, SpecValidationError

TOKENS_DIR = "tokens"
COMPONENTS_DIR = "components"
VOCABULARY_FILE = "vocabulary/css-properties.json"
SCHEMAS_DIR = "schemas"


@dataclass(frozen=True)
class SpecFile:
    """A single parsed JSON document plus where it came from."""

    path: Path
    root: Path
    data: dict

    @property
    def location(self) -> str:
        """Short, stable identifier used in error messages and reports."""
        for base in (Path.cwd(), self.root.parent):
            try:
                return str(self.path.relative_to(base))
            except ValueError:
                continue
        return str(self.path)  # pragma: no cover - defensive


@dataclass
class RawSpec:
    roots: tuple[Path, ...]
    token_files: list[SpecFile] = field(default_factory=list)
    component_files: list[SpecFile] = field(default_factory=list)
    vocabulary_files: list[SpecFile] = field(default_factory=list)
    schemas: dict[str, dict] = field(default_factory=dict)

    @property
    def vocabulary(self) -> dict:
        """Merged CSS vocabulary. Later roots may add properties or states."""
        properties: dict[str, dict] = {}
        states: list[str] = []
        for spec_file in self.vocabulary_files:
            properties.update(spec_file.data.get("properties", {}))
            for state in spec_file.data.get("states", []):
                if state not in states:
                    states.append(state)
        return {"properties": properties, "states": states}


def _read_json(path: Path, errors: list[SpecError]) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(
            SpecError("json-invalid", str(path), f"not valid JSON: {exc}")
        )
        return None


def load_spec(roots: list[Path] | tuple[Path, ...], schemas_dir: Path | None = None) -> RawSpec:
    """Read every spec file under ``roots``. Raises on unreadable/missing pieces."""
    roots = tuple(Path(root).resolve() for root in roots)
    errors: list[SpecError] = []
    spec = RawSpec(roots=roots)

    for root in roots:
        if not root.is_dir():
            errors.append(SpecError("spec-root-missing", str(root), "spec root does not exist"))
            continue
        for kind, target in ((TOKENS_DIR, spec.token_files), (COMPONENTS_DIR, spec.component_files)):
            directory = root / kind
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.json")):
                data = _read_json(path, errors)
                if data is not None:
                    target.append(SpecFile(path=path, root=root, data=data))
        vocabulary = root / VOCABULARY_FILE
        if vocabulary.is_file():
            data = _read_json(vocabulary, errors)
            if data is not None:
                spec.vocabulary_files.append(SpecFile(path=vocabulary, root=root, data=data))

    schema_roots = [schemas_dir] if schemas_dir else [root / SCHEMAS_DIR for root in roots]
    for directory in schema_roots:
        if directory is None or not Path(directory).is_dir():
            continue
        for path in sorted(Path(directory).glob("*.json")):
            data = _read_json(path, errors)
            if data is not None:
                spec.schemas.setdefault(path.name, data)

    if not spec.vocabulary_files:
        errors.append(
            SpecError(
                "vocabulary-missing",
                str(roots[0] if roots else "-"),
                f"no CSS vocabulary found; expected {VOCABULARY_FILE} in one of the spec roots",
            )
        )
    for required in ("tokens.schema.json", "component.schema.json", "css-vocabulary.schema.json"):
        if required not in spec.schemas:
            errors.append(
                SpecError(
                    "schema-missing",
                    str(roots[0] if roots else "-"),
                    f"meta-schema {required} not found in any spec root's schemas/ directory",
                )
            )
    if not spec.token_files:
        errors.append(SpecError("tokens-missing", str(roots[0] if roots else "-"), "no token files found"))
    if not spec.component_files:
        errors.append(SpecError("components-missing", str(roots[0] if roots else "-"), "no component files found"))

    if errors:
        raise SpecValidationError(errors)
    return spec
