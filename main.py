from kubernetes import client, config
from mcp.server.fastmcp import FastMCP

# Configs can be set in Configuration class directly or using helper utility
config.load_kube_config()

mcp = FastMCP("k8s agent")

@mcp.tool()
def list_pods(namespace: str = "default", output_format: str = "table") -> str:
    """
    List all pods in the specified namespace.

    Args:
        namespace (str): The namespace to list pods from. Default is "default".
        output_format (str): The format of the output. Can be "table" or "json". Default is "table".

    Returns:
        str: A formatted string listing the pods.
    """
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace)

    if output_format == "json":
        import json
        pod_list = [pod.to_dict() for pod in pods.items]
        return json.dumps(pod_list, indent=2)
    else:
        pod_info = "NAME\tSTATUS\tNODE\n"
        for pod in pods.items:
            pod_info += f"{pod.metadata.name}\t{pod.status.phase}\t{pod.spec.node_name}\n"
        return pod_info

def main():
    # Initialize and run the server
    mcp.run(transport="sse",)

if __name__ == "__main__":
    main()