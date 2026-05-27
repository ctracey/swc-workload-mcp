.DEFAULT_GOAL := help
.PHONY: help install test test-unit test-integration test-e2e dev

help:  ## List available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## Create the venv and install project + dev deps
	uv venv
	uv pip install -e ".[dev]"

test:  ## Run the full test suite
	uv run pytest

test-unit:  ## Run only the unit tier
	uv run pytest tests/mcp/unit

test-integration:  ## Run only the integration tier
	uv run pytest tests/mcp/integration

test-e2e:  ## Run only the e2e tier
	uv run pytest tests/mcp/e2e

dev:  ## Launch MCP Inspector against the local server
	npx @modelcontextprotocol/inspector uv run swc-workload-mcp
