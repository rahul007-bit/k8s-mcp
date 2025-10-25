.PHONY: help mcp-server cli backend frontend dev stop

help:
	@echo "K8s MCP - Available commands:"
	@echo ""
	@echo "  make mcp-server    - Start MCP server (requires k8s cluster)"
	@echo "  make cli           - Start CLI client"
	@echo "  make backend       - Start FastAPI backend"
	@echo "  make frontend      - Start React frontend"
	@echo "  make dev           - Start all services in background"
	@echo "  make stop          - Stop all background services"
	@echo ""

mcp-server:
	@echo "Starting MCP server..."
	@cd . && uv run k8s_mcp_server.py

cli:
	@echo "Starting CLI client..."
	@cd . && uv run mcp_client.py

backend:
	@echo "Starting backend server..."
	@cd app/backend && uv run run.py

frontend:
	@echo "Starting frontend..."
	@cd app/frontend && bun run dev

dev:
	@echo "Starting all services in background..."
	@echo "Backend: http://localhost:8001"
	@echo "Frontend: http://localhost:5173"
	@echo "MCP Server: :8000"
	@cd app/backend && uv run run.py > /tmp/k8s-mcp-backend.log 2>&1 &
	@sleep 2
	@cd app/frontend && bun run dev > /tmp/k8s-mcp-frontend.log 2>&1 &
	@echo "Services started. Check logs with: make logs"

logs:
	@echo "Backend logs:"
	@tail -f /tmp/k8s-mcp-backend.log &
	@echo "Frontend logs:"
	@tail -f /tmp/k8s-mcp-frontend.log

stop:
	@echo "Stopping all services..."
	@pkill -f "uv run run.py" || true
	@pkill -f "bun run dev" || true
	@echo "All services stopped."

install-deps:
	@echo "Installing dependencies..."
	@cd app/backend && uv sync
	@cd app/frontend && bun install

clean:
	@echo "Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@rm -f /tmp/k8s-mcp-*.log
	@echo "Clean complete."
