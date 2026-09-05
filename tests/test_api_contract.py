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
