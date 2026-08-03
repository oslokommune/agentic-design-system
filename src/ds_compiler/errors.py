"""Structured compile errors.

Every failure carries a machine-readable ``code`` and a ``location`` (file plus a
JSON-ish path into the document) so that an agent editing the spec can act on the
error without parsing prose.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class SpecError:
    code: str
    location: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"[{self.code}] {self.location}: {self.message}"


class SpecValidationError(Exception):
    """Raised when the spec is not compilable. Carries *all* errors found."""

    def __init__(self, errors: list[SpecError]) -> None:
        self.errors: tuple[SpecError, ...] = tuple(errors)
        count = len(self.errors)
        body = "\n".join(f"  - {error}" for error in self.errors)
        super().__init__(f"{count} spec error(s):\n{body}")

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(error.code for error in self.errors)

    def as_dict(self) -> dict:
        return {
            "ok": False,
            "error_count": len(self.errors),
            "errors": [
                {"code": e.code, "location": e.location, "message": e.message}
                for e in self.errors
            ],
        }
