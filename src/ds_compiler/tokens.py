"""Token graph: flatten DTCG token files, resolve aliases, name CSS variables.

Tokens are the *only* place literal values are allowed. Everything downstream
(component styles, generated CSS) refers to tokens, never to literals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterator

from .errors import SpecError
from .loader import SpecFile

ALIAS_RE = re.compile(r"^\{([a-z0-9][a-z0-9.\-]*)\}$")
CSS_VAR_PREFIX = "--ds-"


@dataclass(frozen=True)
class Token:
    ref: str
    path: tuple[str, ...]
    type: str
    value: Any
    alias: str | None
    description: str | None
    source: str

    @property
    def css_var(self) -> str:
        return CSS_VAR_PREFIX + "-".join(self.path)

    @property
    def is_alias(self) -> bool:
        return self.alias is not None


class TokenSet:
    """Ordered mapping of ``group.name`` reference -> :class:`Token`."""

    def __init__(self, tokens: dict[str, Token] | None = None) -> None:
        self._tokens: dict[str, Token] = dict(tokens or {})

    def __contains__(self, ref: object) -> bool:
        return ref in self._tokens

    def __iter__(self) -> Iterator[Token]:
        return iter(self._tokens.values())

    def __len__(self) -> int:
        return len(self._tokens)

    def get(self, ref: str) -> Token | None:
        return self._tokens.get(ref)

    def add(self, token: Token) -> None:
        self._tokens[token.ref] = token

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(self._tokens)

    def resolve(self, ref: str) -> Token | None:
        """Follow the alias chain to the token holding a literal value."""
        seen: set[str] = set()
        token = self._tokens.get(ref)
        while token is not None and token.alias is not None:
            if token.ref in seen:
                return None
            seen.add(token.ref)
            token = self._tokens.get(token.alias)
        return token


def _walk(node: dict, path: tuple[str, ...], inherited_type: str | None) -> Iterator[tuple[tuple[str, ...], dict, str | None]]:
    node_type = node.get("$type", inherited_type)
    for key, value in node.items():
        if key.startswith("$"):
            continue
        if not isinstance(value, dict):
            continue
        child_path = path + (key,)
        if "$value" in value:
            yield child_path, value, value.get("$type", node_type)
        else:
            yield from _walk(value, child_path, value.get("$type", node_type))


def build_token_set(token_files: list[SpecFile], errors: list[SpecError]) -> TokenSet:
    tokens = TokenSet()
    seen_vars: dict[str, str] = {}

    for spec_file in token_files:
        for path, raw, token_type in _walk(spec_file.data, (), None):
            ref = ".".join(path)
            location = f"{spec_file.location}#/{'/'.join(path)}"
            value = raw["$value"]
            alias = None
            if isinstance(value, str):
                match = ALIAS_RE.match(value)
                if match:
                    alias = match.group(1)
            if token_type is None and alias is None:
                errors.append(
                    SpecError(
                        "token-missing-type",
                        location,
                        f"token '{ref}' has no $type and no group $type to inherit",
                    )
                )
                continue
            if ref in tokens:
                errors.append(
                    SpecError("token-duplicate", location, f"token '{ref}' is declared more than once")
                )
                continue
            token = Token(
                ref=ref,
                path=path,
                type=token_type or "",
                value=value,
                alias=alias,
                description=raw.get("$description"),
                source=spec_file.location,
            )
            if token.css_var in seen_vars and seen_vars[token.css_var] != ref:
                errors.append(
                    SpecError(
                        "token-css-var-collision",
                        location,
                        f"token '{ref}' and '{seen_vars[token.css_var]}' both map to CSS variable {token.css_var}",
                    )
                )
                continue
            seen_vars[token.css_var] = ref
            tokens.add(token)

    _validate_aliases(tokens, errors)
    return tokens


def _validate_aliases(tokens: TokenSet, errors: list[SpecError]) -> None:
    for token in list(tokens):
        if token.alias is None:
            continue
        location = f"{token.source}#/{'/'.join(token.path)}"
        target = tokens.get(token.alias)
        if target is None:
            errors.append(
                SpecError(
                    "token-alias-dangling",
                    location,
                    f"token '{token.ref}' aliases unknown token '{token.alias}'",
                )
            )
            continue
        # Cycle detection.
        seen = {token.ref}
        cursor: Token | None = target
        cyclic = False
        while cursor is not None and cursor.alias is not None:
            if cursor.ref in seen:
                cyclic = True
                break
            seen.add(cursor.ref)
            cursor = tokens.get(cursor.alias)
        if cyclic:
            errors.append(
                SpecError(
                    "token-alias-cycle",
                    location,
                    f"alias chain starting at '{token.ref}' is circular",
                )
            )
            continue
        resolved = tokens.resolve(token.ref)
        if resolved is None:
            continue
        if token.type and resolved.type and token.type != resolved.type:
            errors.append(
                SpecError(
                    "token-type-mismatch",
                    location,
                    f"token '{token.ref}' is $type '{token.type}' but resolves to '{resolved.ref}' of $type '{resolved.type}'",
                )
            )


def effective_type(tokens: TokenSet, token: Token) -> str:
    """The $type to validate against - taken from the resolved literal token."""
    if token.type:
        return token.type
    resolved = tokens.resolve(token.ref)
    return resolved.type if resolved else ""
