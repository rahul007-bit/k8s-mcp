.PHONY: help mcp-server cli clean

help:
	@echo "K8s MCP - Available commands:"
	@echo ""
	@echo "  make mcp-server    - Start MCP server (requires k8s cluster)"
	@echo "  make cli           - Start CLI client"
	@echo "  make clean         - Remove cache files"
	@echo ""

mcp-server:
	@echo "Starting MCP server..."
	@cd . && uv run k8s_mcp_server.py

cli:
	@echo "Starting CLI client..."
	@cd . && uv run mcp_client.py

clean:
	@echo "Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete."
