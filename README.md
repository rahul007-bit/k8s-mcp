# K8s MCP

A Kubernetes assistant powered by Model Context Protocol (MCP) and Google Gemini.

## Requirements

- Python 3.10+
- Kubernetes cluster with kubeconfig configured
- Node.js 18+ (for frontend)
- Bun (optional, for faster frontend builds)

## Quick Start

Use the Makefile to run different components:

### 1. MCP Server

Starts the MCP server that communicates with your Kubernetes cluster.

```bash
make mcp-server
```

Requires: Active Kubernetes cluster and configured kubeconfig.

### 2. CLI Mode

Interactive command-line interface to query your Kubernetes cluster.

```bash
make cli
```

### 3. Web Application (Backend + Frontend)

Start the backend API server:

```bash
make backend
```

Start the frontend in another terminal:

```bash
make frontend
```

Then open http://localhost:5173 in your browser.

### 4. All at Once

Start all services in background (development mode):

```bash
make dev
```

## Project Structure

```
k8s_mcp_server.py    - MCP server implementation
mcp_client.py        - CLI client
app/
  backend/           - FastAPI server
  frontend/          - React UI
```

## Configuration

Ensure your kubeconfig is at `~/.kube/config` or set the `KUBECONFIG` environment variable.

The MCP server exposes 32 Kubernetes tools for managing resources, deployments, services, and more.

## Features

- Real-time Kubernetes operations via MCP tools
- Chat interface with tool call results
- Inline tool call display in messages
- WebSocket streaming for live responses
- Automatic WebSocket reconnection

### Make Commands

Available make targets (run `make <target>`):

- `make help` — Show all available commands  
- `make mcp-server` — Start the K8s MCP server  
- `make cli` — Launch the interactive CLI client  
- `make backend` — Start the FastAPI backend  
- `make frontend` — Start the React frontend  
- `make dev` — Start backend and frontend in the background (development mode)  
- `make logs` — Tail service logs  
- `make stop` — Stop all background services  
- `make install-deps` — Install project dependencies  
- `make clean` — Remove build artifacts and cache files
