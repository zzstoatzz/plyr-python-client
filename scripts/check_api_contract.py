"""Check SDK HTTP calls against an OpenAPI document, without making requests."""

import argparse
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def path_pattern(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def shape(value: object, schema: dict, seen: frozenset[str] = frozenset()) -> object:
    if isinstance(value, list):
        return [shape(item, schema, seen) for item in value]
    if not isinstance(value, dict):
        return value
    if "$ref" in value:
        ref = value["$ref"]
        if ref in seen:
            return {"recursive": ref}
        target = schema
        for part in ref.removeprefix("#/").split("/"):
            target = target[part]
        return shape(target, schema, seen | {ref})
    return {
        key: shape(item, schema, seen)
        for key, item in value.items()
        if key not in {"title", "description", "example", "examples", "operationId"}
    }


def check(schema: dict, source: str, baseline: dict | None = None) -> list[str]:
    paths = {
        path_pattern(path): operations for path, operations in schema["paths"].items()
    }
    errors: list[str] = []
    tree = ast.parse(source)
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if (
            node.func.attr not in {"get", "post", "put", "patch", "delete"}
            or not node.args
        ):
            continue
        url = node.args[0]
        if (
            not isinstance(url, ast.Call)
            or not isinstance(url.func, ast.Attribute)
            or url.func.attr != "_url"
        ):
            continue
        path = url.args[0]
        if isinstance(path, ast.Constant):
            route = path.value
        elif isinstance(path, ast.JoinedStr):
            route = "".join(
                part.value if isinstance(part, ast.Constant) else "{}"
                for part in path.values
            )
        else:
            errors.append(
                f"line {node.lineno}: unclassified dynamic URL; extend the contract checker"
            )
            continue
        operation = paths.get(route, {}).get(node.func.attr)
        if operation is not None:
            if baseline is not None:
                previous = {
                    path_pattern(path): ops for path, ops in baseline["paths"].items()
                }.get(route, {}).get(node.func.attr)
                if previous is None:
                    errors.append(
                        f"{route}: refresh the reviewed API contract for this new operation"
                    )
                else:
                    for section in ["responses", "requestBody", "parameters"]:
                        current = operation.get(section)
                        old = previous.get(section)
                        if section == "responses":
                            current = {
                                k: v
                                for k, v in (current or {}).items()
                                if k.startswith("2")
                            }
                            old = {
                                k: v
                                for k, v in (old or {}).items()
                                if k.startswith("2")
                            }
                        if shape(current, schema) != shape(old, baseline):
                            errors.append(
                                f"{node.func.attr.upper()} {route}: {section} changed; review SDK models, CLI/MCP mappings and refresh the contract"
                            )
            allowed = {
                p["name"] for p in operation.get("parameters", []) if p["in"] == "query"
            }
            for keyword in node.keywords:
                if keyword.arg != "params":
                    continue
                values = [keyword.value]
                if isinstance(keyword.value, ast.Name):
                    function = next(
                        fn
                        for fn in functions
                        if fn.lineno <= node.lineno <= fn.end_lineno
                    )
                    values = [
                        n.value
                        for n in ast.walk(function)
                        if isinstance(n, ast.Assign | ast.AnnAssign)
                        and isinstance(n.value, ast.Dict)
                    ]
                    for assignment in ast.walk(function):
                        if (
                            isinstance(assignment, ast.Subscript)
                            and isinstance(assignment.value, ast.Name)
                            and assignment.value.id == keyword.value.id
                            and isinstance(assignment.slice, ast.Constant)
                            and assignment.slice.value not in allowed
                        ):
                            errors.append(
                                f"line {node.lineno}: unknown query field {assignment.slice.value} for {route}"
                            )
                for value in values:
                    if isinstance(value, ast.Dict):
                        for key in value.keys:
                            if (
                                isinstance(key, ast.Constant)
                                and key.value not in allowed
                            ):
                                errors.append(
                                    f"line {node.lineno}: unknown query field {key.value} for {route}"
                                )
        if operation is None:
            errors.append(
                f"line {node.lineno}: {node.func.attr.upper()} {route} absent from API"
            )
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=ROOT / "contracts/http.json")
    args = parser.parse_args()
    errors = check(
        json.loads(args.schema.read_text()),
        (ROOT / "packages/plyrfm/src/plyrfm/client.py").read_text(),
        baseline=json.loads((ROOT / "contracts/http.json").read_text()),
    )
    if errors:
        raise SystemExit("\n".join(errors))
    print("All SDK HTTP methods and paths exist in the API contract")


if __name__ == "__main__":
    main()
