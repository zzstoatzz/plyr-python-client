"""Prove the compatibility gate rejects drift, rather than blessing a snapshot."""

import json
from pathlib import Path

from scripts.check_api_contract import check

ROOT = Path(__file__).resolve().parents[1]


def test_current_sdk_contract() -> None:
    assert not check(
        json.loads((ROOT / "contracts/http.json").read_text()),
        (ROOT / "packages/plyrfm/src/plyrfm/client.py").read_text(),
    )


def test_rejects_removed_route_and_unknown_query() -> None:
    source = 'client.get(self._url("/search/"), params={"q": "ambient", "offset": 1})'
    schema = {
        "paths": {"/search/": {"get": {"parameters": [{"name": "q", "in": "query"}]}}}
    }
    assert "unknown query field offset" in check(schema, source)[0]
    assert "absent from API" in check({"paths": {}}, source)[0]


def test_rejects_response_contract_drift() -> None:
    source = 'client.get(self._url("/tracks/42"))'
    baseline = {
        "paths": {
            "/tracks/42": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {"schema": {"type": "integer"}}
                            }
                        }
                    }
                }
            }
        }
    }
    changed = json.loads(json.dumps(baseline))
    changed["paths"]["/tracks/42"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["type"] = "string"
    assert any(
        "responses changed" in error for error in check(changed, source, baseline)
    )


def object_contract(properties: dict, required: list[str]) -> dict:
    return {
        "paths": {
            "/tracks/42": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": properties,
                                        "required": required,
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


def test_optional_response_addition_works_before_and_after_server_rollout() -> None:
    source = 'client.get(self._url("/tracks/42"))'
    old = object_contract({"id": {"type": "integer"}}, ["id"])
    new = object_contract(
        {"id": {"type": "integer"}, "duration": {"type": "integer"}}, ["id"]
    )
    assert not check(new, source, old)
    assert not check(old, source, new)


def test_optional_response_type_changes_and_required_changes_still_fail() -> None:
    source = 'client.get(self._url("/tracks/42"))'
    old = object_contract(
        {"id": {"type": "integer"}, "duration": {"type": "integer"}}, ["id"]
    )
    changed_type = object_contract(
        {"id": {"type": "integer"}, "duration": {"type": "string"}}, ["id"]
    )
    removed_required = object_contract({"duration": {"type": "integer"}}, [])
    made_required = object_contract(
        {"id": {"type": "integer"}, "duration": {"type": "integer"}},
        ["id", "duration"],
    )
    for changed in [changed_type, removed_required, made_required]:
        assert any(
            "responses changed" in error for error in check(changed, source, old)
        )
