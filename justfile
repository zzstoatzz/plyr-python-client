# plyr-python-client justfile

# deploy prefect flows
deploy-flows:
    uvx prefect --profile pond deploy --all --prefect-file flows/prefect.yaml

# fast, offline interface gates used locally and in CI
check-interfaces:
    uv run pytest tests/test_client_parity.py tests/test_surface_inventory.py tests/test_read_parity.py tests/test_mcp_header_auth.py tests/test_api_contract.py tests/test_download_policy.py tests/test_doc_examples.py -q
    uv run python scripts/check_api_contract.py
    uv run python scripts/render_surfaces.py --check
    uv run python scripts/check_doc_examples.py README.md packages/plyrfm/README.md packages/plyrfm-mcp/README.md

surfaces:
    uv run python scripts/render_surfaces.py

# agent evaluation with MCP tools only (uses Pi's configured credentials)
eval-mcp *args:
    uv run python scripts/pi_harness.py {{args}}
