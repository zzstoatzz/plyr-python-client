# plyr-python-client justfile

# deploy prefect flows
deploy-flows:
    uvx prefect --profile pond deploy --all --prefect-file flows/prefect.yaml
