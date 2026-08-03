"""Standalone Django template engine for a compiled app.

Used by the demo renderer and the test suite: no Django project, no settings
module - just enough configuration to render the generated partials.
"""

from __future__ import annotations

import sys
from pathlib import Path


def configure_django() -> None:
    import django
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DEBUG=True,
            USE_TZ=False,
            INSTALLED_APPS=[],
            DATABASES={},
            TEMPLATES=[],
            SECRET_KEY="ds-compile-standalone",
        )
        django.setup()


def make_engine(out_dir: Path, app_name: str = "ds", extra_dirs: tuple[Path, ...] = ()):
    """A Django template :class:`Engine` that can render the compiled app."""
    configure_django()
    from django.template import Engine

    out_dir = Path(out_dir).resolve()
    if str(out_dir) not in sys.path:
        sys.path.insert(0, str(out_dir))

    dirs = [str(Path(directory).resolve()) for directory in extra_dirs]
    dirs.append(str(out_dir / app_name / "templates"))
    return Engine(dirs=dirs, libraries={"ds": f"{app_name}.templatetags.ds"}, debug=True)
