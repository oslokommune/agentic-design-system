"""Verbatim runtime sources copied into the compiled Django app.

``ds_runtime.py`` is *not* imported by the compiler (it imports the generated
``spec`` module, which only exists in the output). It is treated as a file
resource: see :func:`ds_compiler.runtime.runtime_source`.
"""

from __future__ import annotations

from pathlib import Path

RUNTIME_FILE = Path(__file__).with_name("ds_runtime.py")


def runtime_source() -> str:
    return RUNTIME_FILE.read_text(encoding="utf-8")
