# K8s MCP

A Kubernetes assistant powered by Model Context Protocol (MCP) and Google Gemini.

## Requirements

- Python 3.10+
- Kubernetes cluster with kubeconfig configured

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

## Project Structure

```
k8s_mcp_server.py    - MCP server implementation
mcp_client.py        - CLI client
```

## Configuration

Ensure your kubeconfig is at `~/.kube/config` or set the `KUBECONFIG` environment variable.

The MCP server exposes 32+ Kubernetes tools for managing resources, deployments, services, and more, including long-running background tasks.

## Features

- Real-time Kubernetes operations via MCP tools
- Interactive chat interface with tool call results
- Inline tool call display in messages
- Background task execution and asynchronous event streaming
- Session persistence

### Make Commands

Available make targets (run `make <target>`):

- `make help` — Show all available commands  
- `make mcp-server` — Start the K8s MCP server  
- `make cli` — Launch the interactive CLI client  
- `make clean` — Remove build artifacts and cache files
