"""Compilation pipeline: load -> validate -> emit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .emit import write_app
from .loader import load_spec
from .model import ValidatedSpec
from .validate import validate_spec

DEFAULT_SPEC_ROOT = Path("spec")
DEFAULT_OUT_DIR = Path("build")
DEFAULT_APP_NAME = "ds"


@dataclass(frozen=True)
class CompileResult:
    spec: ValidatedSpec
    out_dir: Path
    app_dir: Path
    app_name: str
    written: tuple[Path, ...]

    @property
    def overrides_report(self) -> Path:
        return self.out_dir / "overrides-report.json"

    def summary(self) -> dict:
        return {
            "ok": True,
            "out_dir": str(self.out_dir),
            "app": self.app_name,
            "tokens": len(self.spec.tokens),
            "components": [component.name for component in self.spec.components],
            "overrides": len(self.spec.overrides),
            "files_written": len(self.written),
        }


def load_and_validate(
    spec_roots: list[Path] | tuple[Path, ...] = (DEFAULT_SPEC_ROOT,),
    schemas_dir: Path | None = None,
) -> ValidatedSpec:
    """Steps 0-1. Raises :class:`~ds_compiler.errors.SpecValidationError` on any problem."""
    return validate_spec(load_spec(list(spec_roots), schemas_dir=schemas_dir))


def compile_spec(
    spec_roots: list[Path] | tuple[Path, ...] = (DEFAULT_SPEC_ROOT,),
    out_dir: Path = DEFAULT_OUT_DIR,
    app_name: str = DEFAULT_APP_NAME,
    schemas_dir: Path | None = None,
    clean: bool = True,
) -> CompileResult:
    """Validate the spec and emit the Django app package."""
    spec = load_and_validate(spec_roots, schemas_dir=schemas_dir)
    out_dir = Path(out_dir)
    written = write_app(spec, out_dir, app_name=app_name, clean=clean)
    return CompileResult(
        spec=spec,
        out_dir=out_dir,
        app_dir=out_dir / app_name,
        app_name=app_name,
        written=tuple(written),
    )
