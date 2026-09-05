"""Validate documented SDK calls without executing examples or making requests."""

import argparse
import ast
import inspect
import re
from pathlib import Path

from plyrfm import PlyrClient


def check(text: str, client: PlyrClient) -> list[str]:
    errors: list[str] = []
    for block in re.findall(r"```python\s*\n(.*?)```", text, re.DOTALL):
        if not re.search(r"\b(?:client|authed)\.", block):
            continue
        try:
            tree = ast.parse(block)
        except SyntaxError as exc:
            errors.append(f"invalid Python example: {exc.msg}")
            continue
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call):
                continue
            node = call.func
            names: list[str] = []
            while isinstance(node, ast.Attribute):
                names.insert(0, node.attr)
                node = node.value
            if not isinstance(node, ast.Name) or node.id not in {"client", "authed"}:
                continue
            if not names:
                continue
            try:
                target = client
                for name in names:
                    target = getattr(target, name)
                inspect.signature(target).bind(
                    *[object() for _ in call.args],
                    **{
                        keyword.arg: object()
                        for keyword in call.keywords
                        if keyword.arg
                    },
                )
            except (AttributeError, TypeError, ValueError) as exc:
                errors.append(f"{node.id}.{'.'.join(names)}: {exc}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="+")
    args = parser.parse_args()
    files: set[Path] = set()
    for path in args.paths:
        if path.is_dir():
            files.update(path.rglob("*.md"))
            files.update(path.rglob("*.mdx"))
        else:
            files.add(path)
    failures: list[str] = []
    with PlyrClient() as client:
        for path in sorted(files):
            failures.extend(
                f"{path}: {error}" for error in check(path.read_text(), client)
            )
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"SDK examples checked in {len(files)} documentation files (no execution)")


if __name__ == "__main__":
    main()
