"""Render the demo page with the compiled design system.

Usage::

    uv run python demo/render_demo.py

Compiles the core spec *plus* ``demo/spec`` (which adds the one component that
uses the escape hatch) into ``demo/build/``, then renders ``demo/page.html`` to
``demo/out.html`` with a standalone Django template engine - no Django project
needed.
"""

from __future__ import annotations

import json
from pathlib import Path

from ds_compiler import compile_spec
from ds_compiler.django_env import make_engine

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo"

CONTEXT = {
    "dynamic_label": "From context",
}


def main() -> int:
    result = compile_spec(
        [ROOT / "spec", DEMO / "spec"],
        out_dir=DEMO / "build",
        app_name="ds",
    )

    from django.template import Context

    engine = make_engine(DEMO / "build", app_name="ds", extra_dirs=(DEMO,))
    html = engine.get_template("page.html").render(Context(CONTEXT))
    out_file = DEMO / "out.html"
    out_file.write_text(html, encoding="utf-8")

    report = json.loads(result.overrides_report.read_text(encoding="utf-8"))
    print(f"compiled  {len(result.spec.components)} components, {len(result.spec.tokens)} tokens -> {result.out_dir}")
    print(f"rendered  {out_file.relative_to(ROOT)} ({len(html)} bytes)")
    print(f"overrides {report['count']}:")
    for override in report["overrides"]:
        print(f"  - {override['id']} in {override['component']} ({override['selector']})")
        print(f"    reason: {override['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
