"""``ds-compile`` command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compile import DEFAULT_APP_NAME, DEFAULT_OUT_DIR, DEFAULT_SPEC_ROOT, compile_spec, load_and_validate
from .errors import SpecValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ds-compile",
        description=(
            "Compile the declarative design system spec into a Django app "
            "(template tags, partials, CSS) plus an overrides report."
        ),
    )
    parser.add_argument(
        "--spec",
        dest="spec_roots",
        action="append",
        type=Path,
        metavar="DIR",
        help=f"spec root (repeatable; later roots extend earlier ones). Default: {DEFAULT_SPEC_ROOT}",
    )
    parser.add_argument(
        "--out", dest="out_dir", type=Path, default=DEFAULT_OUT_DIR, metavar="DIR",
        help=f"output directory. Default: {DEFAULT_OUT_DIR}",
    )
    parser.add_argument(
        "--app-name", default=DEFAULT_APP_NAME, metavar="NAME",
        help=f"python package name of the generated Django app. Default: {DEFAULT_APP_NAME}",
    )
    parser.add_argument(
        "--schemas", dest="schemas_dir", type=Path, default=None, metavar="DIR",
        help="directory holding the meta-schemas. Default: <first spec root>/schemas",
    )
    parser.add_argument("--check", action="store_true", help="validate only, emit nothing")
    parser.add_argument("--json", action="store_true", help="machine-readable output on stdout")
    parser.add_argument("-q", "--quiet", action="store_true", help="only report failures")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec_roots = args.spec_roots or [DEFAULT_SPEC_ROOT]

    try:
        if args.check:
            spec = load_and_validate(spec_roots, schemas_dir=args.schemas_dir)
            payload = {
                "ok": True,
                "checked": [str(root) for root in spec_roots],
                "tokens": len(spec.tokens),
                "components": [component.name for component in spec.components],
                "overrides": len(spec.overrides),
            }
        else:
            result = compile_spec(
                spec_roots,
                out_dir=args.out_dir,
                app_name=args.app_name,
                schemas_dir=args.schemas_dir,
            )
            payload = result.summary()
    except SpecValidationError as error:
        if args.json:
            json.dump(error.as_dict(), sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print(f"ds-compile: FAILED - {len(error.errors)} spec error(s)", file=sys.stderr)
            for item in error.errors:
                print(f"  {item}", file=sys.stderr)
        return 1

    if args.json:
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif not args.quiet:
        if args.check:
            print(
                f"ds-compile: spec OK - {payload['tokens']} tokens, "
                f"{len(payload['components'])} components, {payload['overrides']} override(s)"
            )
        else:
            print(
                f"ds-compile: wrote {payload['files_written']} files to {payload['out_dir']} "
                f"(app '{payload['app']}': {payload['tokens']} tokens, "
                f"{len(payload['components'])} components, {payload['overrides']} override(s))"
            )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
