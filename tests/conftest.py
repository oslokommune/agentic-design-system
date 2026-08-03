"""Shared fixtures: a compiled design system plus a standalone Django engine."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable

import pytest

from ds_compiler import compile_spec, load_and_validate
from ds_compiler.django_env import make_engine

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_ROOT = REPO_ROOT / "spec"
DEMO_SPEC_ROOT = REPO_ROOT / "demo" / "spec"


@pytest.fixture(scope="session")
def spec_root() -> Path:
    return SPEC_ROOT


@pytest.fixture(scope="session")
def demo_spec_root() -> Path:
    return DEMO_SPEC_ROOT


@pytest.fixture(scope="session")
def validated():
    """The core spec, loaded and validated."""
    return load_and_validate([SPEC_ROOT])


@pytest.fixture(scope="session")
def compiled(tmp_path_factory):
    """The core spec compiled into a Django app named ``ds``."""
    out_dir = tmp_path_factory.mktemp("compiled")
    return compile_spec([SPEC_ROOT], out_dir=out_dir, app_name="ds")


@pytest.fixture(scope="session")
def engine(compiled):
    return make_engine(compiled.out_dir, app_name=compiled.app_name)


@pytest.fixture(scope="session")
def render(engine) -> Callable[..., str]:
    """Render a template string against the compiled design system."""
    from django.template import Context

    def _render(source: str, **context) -> str:
        return engine.from_string(source).render(Context(context))

    return _render


@pytest.fixture(scope="session")
def ds_runtime(engine):
    """The runtime module of the compiled app (for its exception types)."""
    import importlib

    return importlib.import_module("ds.runtime")


@pytest.fixture
def spec_copy(tmp_path) -> Callable[[], Path]:
    """A writable copy of the real spec, for negative tests."""

    def _copy() -> Path:
        destination = tmp_path / "spec"
        shutil.copytree(SPEC_ROOT, destination)
        return destination

    return _copy


def patch_json(path: Path, mutate: Callable[[dict], None]) -> None:
    """Load ``path``, apply ``mutate`` in place, write it back."""
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
