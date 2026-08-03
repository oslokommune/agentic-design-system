"""Compiler for an agent-operated design system.

The source of truth is the JSON spec under ``spec/``: W3C DTCG token files plus
one file per component. This package turns that spec into a Django app, and
hard-fails on anything that would let an un-tokenised value into the system.

Public API::

    from ds_compiler import compile_spec, load_and_validate, SpecValidationError
"""

from .compile import CompileResult, compile_spec, load_and_validate
from .errors import SpecError, SpecValidationError
from .model import Component, OverrideRecord, Prop, ValidatedSpec
from .tokens import Token, TokenSet

__all__ = [
    "CompileResult",
    "Component",
    "OverrideRecord",
    "Prop",
    "SpecError",
    "SpecValidationError",
    "Token",
    "TokenSet",
    "ValidatedSpec",
    "compile_spec",
    "load_and_validate",
]
