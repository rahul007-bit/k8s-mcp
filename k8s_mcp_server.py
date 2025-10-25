"""
Enhanced K8s MCP Server with Multiple Tools
This extends your original server with additional Kubernetes operations
"""

import json
import datetime
from kubernetes import client, config
from mcp.server.fastmcp import FastMCP
from kubernetes.stream import stream
from typing import List, Optional, Dict, Any
from kubernetes.client.exceptions import ApiException


# Load Kubernetes configuration
config.load_kube_config()

# Initialize MCP server
mcp = FastMCP("k8s-agent")


@mcp.tool()
def list_pods(namespace: str = "default", output_format: str = "table", show_labels: bool = False, all_namespaces: bool = False) -> str:
    """
    List all pods in the specified namespace.
    
    Args:
        namespace (str): The namespace to list pods from. Default is "default".
        output_format (str): Output format: "table", "json", "yaml", "wide". Default is "table".
        show_labels (bool): Show pod labels. Default is False.
        all_namespaces (bool): List pods from all namespaces. Default is False.
    
    Returns:
        str: A formatted string listing the pods.
    """
    v1 = client.CoreV1Api()
    
    if all_namespaces:
        pods = v1.list_pod_for_all_namespaces()
    else:
        pods = v1.list_namespaced_pod(namespace)
    
    if output_format == "json":
        pod_list = [pod.to_dict() for pod in pods.items]
        return json.dumps(pod_list, indent=2)
    elif output_format == "yaml":
        import yaml
        pod_list = [pod.to_dict() for pod in pods.items]
        return yaml.dump(pod_list, default_flow_style=False)
    elif output_format == "wide":
        pod_info = "NAMESPACE\tNAME\tREADY\tSTATUS\tRESTARTS\tAGE\tIP\tNODE\n"
        for pod in pods.items:
            ns = pod.metadata.namespace
            name = pod.metadata.name
            ready = len([c for c in (pod.status.container_statuses or []) if c.ready])
            total = len(pod.spec.containers)
            status = pod.status.phase
            restarts = sum([c.restart_count for c in (pod.status.container_statuses or [])])
            age = (datetime.datetime.now(datetime.timezone.utc) - pod.metadata.creation_timestamp).seconds // 60
            ip = pod.status.pod_ip or "N/A"
            node = pod.spec.node_name or "N/A"
            pod_info += f"{ns}\t{name}\t{ready}/{total}\t{status}\t{restarts}\t{age}m\t{ip}\t{node}\n"
        return pod_info
    else:  # table format (default)
        pod_info = "NAMESPACE\tNAME\tREADY\tSTATUS\tRESTARTS\tAGE\n"
        if show_labels:
            pod_info = "NAMESPACE\tNAME\tREADY\tSTATUS\tRESTARTS\tAGE\tLABELS\n"
        for pod in pods.items:
            ns = pod.metadata.namespace
            name = pod.metadata.name
            ready = len([c for c in (pod.status.container_statuses or []) if c.ready])
            total = len(pod.spec.containers)
            status = pod.status.phase
            restarts = sum([c.restart_count for c in (pod.status.container_statuses or [])])
            age = (datetime.datetime.now(datetime.timezone.utc) - pod.metadata.creation_timestamp).seconds // 60
            labels = ",".join([f"{k}={v}" for k, v in (pod.metadata.labels or {}).items()]) if show_labels else ""
            if show_labels:
                pod_info += f"{ns}\t{name}\t{ready}/{total}\t{status}\t{restarts}\t{age}m\t{labels}\n"
            else:
                pod_info += f"{ns}\t{name}\t{ready}/{total}\t{status}\t{restarts}\t{age}m\n"
        return pod_info


@mcp.tool()
def get_pod_logs(pod_name: str, namespace: str = "default", tail_lines: int = 50, follow: bool = False, previous: bool = False, container: Optional[str] = None) -> str:
    """
    Get logs from a specific pod.
    
    Args:
        pod_name (str): Name of the pod
        namespace (str): The namespace of the pod. Default is "default".
        tail_lines (int): Number of log lines to retrieve. Default is 50.
        follow (bool): Follow log output. Default is False.
        previous (bool): Get logs from previous container instance. Default is False.
        container (str): Container name. Default is None (first container).
    
    Returns:
        str: Pod logs
    """
    v1 = client.CoreV1Api()
    
    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
            previous=previous,
            container=container
        )
        return logs
    except Exception as e:
        return f"Error retrieving pod logs: {e}"


@mcp.tool()
def list_deployments(namespace: str = "default", output_format: str = "table", show_labels: bool = False, all_namespaces: bool = False) -> str:
    """
    List all deployments in the specified namespace.
    
    Args:
        namespace (str): The namespace to list deployments from. Default is "default".
        output_format (str): Output format: "table", "json", "yaml", "wide". Default is "table".
        show_labels (bool): Show deployment labels. Default is False.
        all_namespaces (bool): List deployments from all namespaces. Default is False.
    
    Returns:
        str: A formatted string listing the deployments.
    """
    apps_v1 = client.AppsV1Api()
    
    if all_namespaces:
        deployments = apps_v1.list_deployment_for_all_namespaces()
    else:
        deployments = apps_v1.list_namespaced_deployment(namespace)
    
    if output_format == "json":
        deploy_list = [d.to_dict() for d in deployments.items]
        return json.dumps(deploy_list, indent=2)
    elif output_format == "yaml":
        import yaml
        deploy_list = [d.to_dict() for d in deployments.items]
        return yaml.dump(deploy_list, default_flow_style=False)
    elif output_format == "wide":
        deploy_info = "NAMESPACE\tNAME\tREADY\tUP-TO-DATE\tAVAILABLE\tAGE\tIMAGES\n"
        for deploy in deployments.items:
            ns = deploy.metadata.namespace
            name = deploy.metadata.name
            desired = deploy.spec.replicas or 0
            ready = deploy.status.ready_replicas or 0
            updated = deploy.status.updated_replicas or 0
            age = (datetime.datetime.now(datetime.timezone.utc) - deploy.metadata.creation_timestamp).seconds // 60
            images = ",".join([c.image for c in deploy.spec.template.spec.containers])
            deploy_info += f"{ns}\t{name}\t{ready}/{desired}\t{updated}\t{ready}\t{age}m\t{images}\n"
        return deploy_info
    else:  # table format (default)
        deploy_info = "NAME\tREADY\tUP-TO-DATE\tAVAILABLE\tAGE\n"
        if show_labels:
            deploy_info = "NAME\tREADY\tUP-TO-DATE\tAVAILABLE\tAGE\tLABELS\n"
        for deploy in deployments.items:
            name = deploy.metadata.name
            desired = deploy.spec.replicas or 0
            ready = deploy.status.ready_replicas or 0
            updated = deploy.status.updated_replicas or 0
            age = (datetime.datetime.now(datetime.timezone.utc) - deploy.metadata.creation_timestamp).seconds // 60
            labels = ",".join([f"{k}={v}" for k, v in (deploy.metadata.labels or {}).items()]) if show_labels else ""
            if show_labels:
                deploy_info += f"{name}\t{ready}/{desired}\t{updated}\t{ready}\t{age}m\t{labels}\n"
            else:
                deploy_info += f"{name}\t{ready}/{desired}\t{updated}\t{ready}\t{age}m\n"
        return deploy_info


@mcp.tool()
def list_services(namespace: str = "default", output_format: str = "table", all_namespaces: bool = False) -> str:
    """
    List all services in the specified namespace.
    
    Args:
        namespace (str): The namespace to list services from. Default is "default".
        output_format (str): Output format: "table", "json", "yaml", "wide". Default is "table".
        all_namespaces (bool): List services from all namespaces. Default is False.
    
    Returns:
        str: A formatted string listing the services.
    """
    v1 = client.CoreV1Api()
    
    if all_namespaces:
        services = v1.list_service_for_all_namespaces()
    else:
        services = v1.list_namespaced_service(namespace)
    
    if output_format == "json":
        svc_list = [s.to_dict() for s in services.items]
        return json.dumps(svc_list, indent=2)
    elif output_format == "yaml":
        import yaml
        svc_list = [s.to_dict() for s in services.items]
        return yaml.dump(svc_list, default_flow_style=False)
    else:  # table format (default)
        svc_info = "NAME\tTYPE\tCLUSTER-IP\tEXTERNAL-IP\tPORT(S)\tAGE\n"
        for svc in services.items:
            name = svc.metadata.name
            svc_type = svc.spec.type
            cluster_ip = svc.spec.cluster_ip or "N/A"
            external_ip = svc.status.load_balancer.ingress[0].ip if (svc.status.load_balancer and svc.status.load_balancer.ingress) else "N/A"
            ports = ",".join([f"{p.port}/{p.protocol}" for p in (svc.spec.ports or [])])
            age = (datetime.datetime.now(datetime.timezone.utc) - svc.metadata.creation_timestamp).seconds // 60
            svc_info += f"{name}\t{svc_type}\t{cluster_ip}\t{external_ip}\t{ports}\t{age}m\n"
        return svc_info


@mcp.tool()
def list_namespaces(output_format: str = "table") -> str:
    """
    List all namespaces.
    
    Args:
        output_format (str): Output format: "table", "json", "yaml". Default is "table".
    
    Returns:
        str: A formatted string listing the namespaces.
    """
    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace()
    
    if output_format == "json":
        ns_list = [ns.to_dict() for ns in namespaces.items]
        return json.dumps(ns_list, indent=2)
    elif output_format == "yaml":
        import yaml
        ns_list = [ns.to_dict() for ns in namespaces.items]
        return yaml.dump(ns_list, default_flow_style=False)
    else:  # table format
        ns_info = "NAME\tSTATUS\tAGE\n"
        for ns in namespaces.items:
            name = ns.metadata.name
            status = ns.status.phase
            age = (datetime.datetime.now(datetime.timezone.utc) - ns.metadata.creation_timestamp).seconds // 60
            ns_info += f"{name}\t{status}\t{age}m\n"
        return ns_info


@mcp.tool()
def get_pod_status(pod_name: str, namespace: str = "default", output_format: str = "table") -> str:
    """
    Get detailed status of a pod.
    
    Args:
        pod_name (str): Name of the pod
        namespace (str): The namespace of the pod. Default is "default".
        output_format (str): Output format: "table", "json", "yaml". Default is "table".
    
    Returns:
        str: Pod status information
    """
    v1 = client.CoreV1Api()

    def _get(obj, *attrs, default=None):
        """
        Safe getter that supports both object attributes and dict keys,
        returns default if any intermediate value is None or missing.
        """
        val = obj
        for a in attrs:
            if val is None:
                return default
            if isinstance(val, dict):
                val = val.get(a)
            else:
                val = getattr(val, a, None)
        return default if val is None else val

    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        
        if output_format == "json":
            # pod may be a V1Pod-like object
            try:
                return json.dumps(pod.to_dict(), indent=2)
            except Exception:
                # fallback: try to serialize as-is
                return json.dumps(pod, default=str, indent=2)
        elif output_format == "yaml":
            import yaml
            try:
                return yaml.dump(pod.to_dict(), default_flow_style=False)
            except Exception:
                return yaml.dump(pod, default_flow_style=False)
        else:  # table format (safe attribute access)
            name = _get(pod, "metadata", "name", default="N/A")
            ns = _get(pod, "metadata", "namespace", default="N/A")
            status = _get(pod, "status", "phase", default="N/A")
            ip = _get(pod, "status", "pod_ip", default="N/A")
            node = _get(pod, "spec", "node_name", default="N/A")
            containers = _get(pod, "spec", "containers", default=[]) or []

            info = f"Name: {name}\n"
            info += f"Namespace: {ns}\n"
            info += f"Status: {status}\n"
            info += f"IP: {ip}\n"
            info += f"Node: {node}\n"
            info += f"Containers:\n"
            for c in containers:
                cname = _get(c, "name", default=str(c))
                cimage = _get(c, "image", default="N/A")
                info += f"  - {cname}: {cimage}\n"
            return info
    except Exception as e:
        return f"Error getting pod status: {e}"


@mcp.tool()
def describe_pod(pod_name: str, namespace: str = "default") -> str:
    """
    Return detailed pod object as JSON.
    
    Args:
        pod_name (str): Name of the pod
        namespace (str): The namespace of the pod. Default is "default".
    
    Returns:
        str: Detailed pod information
    """
    v1 = client.CoreV1Api()
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        return json.dumps(pod.to_dict(), indent=2)
    except Exception as e:
        return f"Error describing pod: {e}"


@mcp.tool()
def delete_pod(pod_name: str, namespace: str = "default", grace_period_seconds: int = 30, force: bool = False) -> str:
    """
    Delete a pod.
    
    Args:
        pod_name (str): Name of the pod
        namespace (str): The namespace of the pod. Default is "default".
        grace_period_seconds (int): Grace period for pod termination. Default is 30.
        force (bool): Force delete the pod. Default is False.
    
    Returns:
        str: Deletion status
    """
    v1 = client.CoreV1Api()
    try:
        v1.delete_namespaced_pod(
            name=pod_name,
            namespace=namespace,
            grace_period_seconds=grace_period_seconds,
            propagation_policy="Foreground" if force else "Background"
        )
        return f"Pod {pod_name} deleted successfully."
    except ApiException as e:
        return f"API error deleting pod: {e.status} {e.reason}"
    except Exception as e:
        return f"Error deleting pod: {e}"


@mcp.tool()
def patch_pod(pod_name: str, namespace: str = "default", patch_data: Dict[str, Any] = None) -> str:
    """
    Patch a pod with custom data.
    
    Args:
        pod_name (str): Name of the pod
        namespace (str): The namespace of the pod. Default is "default".
        patch_data (dict): Patch data to apply (JSON format)
    
    Returns:
        str: Patch status
    """
    v1 = client.CoreV1Api()
    try:
        if patch_data is None:
            patch_data = {}
        v1.patch_namespaced_pod(name=pod_name, namespace=namespace, body=patch_data)
        return f"Pod {pod_name} patched successfully."
    except Exception as e:
        return f"Error patching pod: {e}"


@mcp.tool()
def patch_deployment(deployment_name: str, namespace: str = "default", patch_data: Dict[str, Any] = None) -> str:
    """
    Patch a deployment with custom data.
    
    Args:
        deployment_name (str): Name of the deployment
        namespace (str): The namespace of the deployment. Default is "default".
        patch_data (dict): Patch data to apply (JSON format)
    
    Returns:
        str: Patch status
    """
    apps_v1 = client.AppsV1Api()
    try:
        if patch_data is None:
            patch_data = {}
        apps_v1.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=patch_data)
        return f"Deployment {deployment_name} patched successfully."
    except Exception as e:
        return f"Error patching deployment: {e}"


@mcp.tool()
def exec_in_pod(pod_name: str, namespace: str = "default", command: Optional[List[str]] = None, container: Optional[str] = None) -> str:
    """
    Execute a command inside a pod.
    
    Args:
        pod_name (str): Name of the pod
        namespace (str): The namespace of the pod. Default is "default".
        command (list): Command to execute as a list. Default is ["/bin/sh", "-c", "echo hello"]
        container (str): Container name. Default is None (first container).
    
    Returns:
        str: Command output
    """
    if command is None:
        command = ["/bin/sh", "-c", "echo hello"]
    v1 = client.CoreV1Api()
    try:
        out = stream(
            v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            command=command,
            container=container,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        return out
    except Exception as e:
        return f"Error executing command in pod: {e}"


@mcp.tool()
def scale_deployment(deployment: str, namespace: str = "default", replicas: int = 1) -> str:
    """
    Scale a deployment to the desired replicas.
    
    Args:
        deployment (str): Name of the deployment
        namespace (str): The namespace of the deployment. Default is "default".
        replicas (int): Desired number of replicas. Default is 1.
    
    Returns:
        str: Scale status
    """
    apps_v1 = client.AppsV1Api()
    try:
        body = {"spec": {"replicas": replicas}}
        apps_v1.patch_namespaced_deployment(name=deployment, namespace=namespace, body=body)
        return f"Scaled deployment {deployment} to {replicas} replicas."
    except Exception as e:
        return f"Error scaling deployment: {e}"


@mcp.tool()
def rollout_restart_deployment(deployment: str, namespace: str = "default") -> str:
    """
    Trigger a rollout restart for a deployment.
    
    Args:
        deployment (str): Name of the deployment
        namespace (str): The namespace of the deployment. Default is "default".
    
    Returns:
        str: Rollout restart status
    """
    apps_v1 = client.AppsV1Api()
    try:
        ts = datetime.datetime.utcnow().isoformat() + "Z"
        body = {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": ts}}}}}
        apps_v1.patch_namespaced_deployment(name=deployment, namespace=namespace, body=body)
        return f"Triggered rollout restart for deployment {deployment}."
    except Exception as e:
        return f"Error triggering rollout restart: {e}"


@mcp.tool()
def list_nodes(output_format: str = "table", show_labels: bool = False) -> str:
    """
    List cluster nodes with basic info.
    
    Args:
        output_format (str): Output format: "table", "json", "yaml", "wide". Default is "table".
        show_labels (bool): Show node labels. Default is False.
    
    Returns:
        str: Node information
    """
    v1 = client.CoreV1Api()
    try:
        nodes = v1.list_node()
        
        if output_format == "json":
            node_list = [n.to_dict() for n in nodes.items]
            return json.dumps(node_list, indent=2)
        elif output_format == "yaml":
            import yaml
            node_list = [n.to_dict() for n in nodes.items]
            return yaml.dump(node_list, default_flow_style=False)
        elif output_format == "wide":
            out = "NAME\tSTATUS\tROLES\tINTERNAL-IP\tEXTERNAL-IP\tOS-IMAGE\tKERNEL-VERSION\tAGE\n"
            for n in nodes.items:
                name = n.metadata.name
                status = n.status.conditions[-1].type if n.status.conditions else "Unknown"
                labels = n.metadata.labels or {}
                roles = ",".join([k.split("/")[-1] for k in labels.keys() if k.startswith("node-role.kubernetes.io/")]) or "none"
                internal_ip = "N/A"
                external_ip = "N/A"
                for addr in (n.status.addresses or []):
                    if addr.type == "InternalIP":
                        internal_ip = addr.address
                    elif addr.type == "ExternalIP":
                        external_ip = addr.address
                node_info = n.status.node_info if n.status else None
                os_image = node_info.os_image if node_info else "N/A"
                kernel = node_info.kernel_version if node_info else "N/A"
                age = (datetime.datetime.now(datetime.timezone.utc) - n.metadata.creation_timestamp).days
                out += f"{name}\t{status}\t{roles}\t{internal_ip}\t{external_ip}\t{os_image}\t{kernel}\t{age}d\n"
            return out
        else:  # table format
            out = "NAME\tSTATUS\tROLES\tAGE\n"
            if show_labels:
                out = "NAME\tSTATUS\tROLES\tAGE\tLABELS\n"
            for n in nodes.items:
                name = n.metadata.name
                status = n.status.conditions[-1].type if n.status.conditions else "Unknown"
                labels = n.metadata.labels or {}
                roles = ",".join([k.split("/")[-1] for k in labels.keys() if k.startswith("node-role.kubernetes.io/")]) or "none"
                age = (datetime.datetime.now(datetime.timezone.utc) - n.metadata.creation_timestamp).days
                labels_str = ",".join([f"{k}={v}" for k, v in labels.items()]) if show_labels else ""
                if show_labels:
                    out += f"{name}\t{status}\t{roles}\t{age}d\t{labels_str}\n"
                else:
                    out += f"{name}\t{status}\t{roles}\t{age}d\n"
            return out
    except Exception as e:
        return f"Error listing nodes: {e}"


@mcp.tool()
def cordon_node(node_name: str) -> str:
    """
    Mark a node unschedulable (cordon).
    
    Args:
        node_name (str): Name of the node
    
    Returns:
        str: Cordon status
    """
    v1 = client.CoreV1Api()
    try:
        body = {"spec": {"unschedulable": True}}
        v1.patch_node(node_name, body=body)
        return f"Node {node_name} cordoned."
    except Exception as e:
        return f"Error cordoning node: {e}"


@mcp.tool()
def uncordon_node(node_name: str) -> str:
    """
    Remove unschedulable from a node (uncordon).
    
    Args:
        node_name (str): Name of the node
    
    Returns:
        str: Uncordon status
    """
    v1 = client.CoreV1Api()
    try:
        body = {"spec": {"unschedulable": False}}
        v1.patch_node(node_name, body=body)
        return f"Node {node_name} uncordoned."
    except Exception as e:
        return f"Error uncordoning node: {e}"


@mcp.tool()
def get_events(namespace: str = "default", involved_object_kind: Optional[str] = None, involved_object_name: Optional[str] = None, limit: int = 100, output_format: str = "table") -> str:
    """
    List recent events in a namespace.
    
    Args:
        namespace (str): The namespace. Default is "default".
        involved_object_kind (str): Filter by object kind. Default is None.
        involved_object_name (str): Filter by object name. Default is None.
        limit (int): Maximum number of events to return. Default is 100.
        output_format (str): Output format: "table", "json", "yaml". Default is "table".
    
    Returns:
        str: Event information
    """
    v1 = client.CoreV1Api()
    try:
        selectors = []
        if involved_object_kind:
            selectors.append(f"involvedObject.kind={involved_object_kind}")
        if involved_object_name:
            selectors.append(f"involvedObject.name={involved_object_name}")
        field_selector = ",".join(selectors) if selectors else None
        events = v1.list_namespaced_event(namespace=namespace, field_selector=field_selector, limit=limit)
        
        if output_format == "json":
            event_list = [e.to_dict() for e in events.items]
            return json.dumps(event_list, indent=2)
        elif output_format == "yaml":
            import yaml
            event_list = [e.to_dict() for e in events.items]
            return yaml.dump(event_list, default_flow_style=False)
        else:  # table format
            out = "LAST-SEEN\tTYPE\tREASON\tOBJECT\tMESSAGE\n"
            for e in events.items:
                last_seen = e.last_timestamp or e.event_time or e.metadata.creation_timestamp
                obj = f"{e.involved_object.kind}/{e.involved_object.name}" if e.involved_object else "N/A"
                out += f"{last_seen}\t{e.type}\t{e.reason}\t{obj}\t{e.message}\n"
            return out
    except Exception as e:
        return f"Error listing events: {e}"


@mcp.tool()
def create_namespace(name: str) -> str:
    """
    Create a new namespace.
    
    Args:
        name (str): Name of the namespace
    
    Returns:
        str: Creation status
    """
    v1 = client.CoreV1Api()
    try:
        body = client.V1Namespace(metadata=client.V1ObjectMeta(name=name))
        v1.create_namespace(body=body)
        return f"Namespace {name} created."
    except ApiException as e:
        if e.status == 409:
            return f"Namespace {name} already exists."
        return f"API error creating namespace: {e}"
    except Exception as e:
        return f"Error creating namespace: {e}"


@mcp.tool()
def apply_yaml(yaml_content: str, namespace: str = "default") -> str:
    """
    Apply Kubernetes resources from YAML content (upsert: create if missing, patch if exists).

    Args:
        yaml_content (str): YAML content as a string
        namespace (str): Namespace to apply resources in. Default is "default".

    Returns:
        str: Application status
    """
    try:
        import yaml
        resources = yaml.safe_load_all(yaml_content)

        results = []
        for resource in resources:
            if resource is None:
                continue

            kind = resource.get("kind", "Unknown")
            name = resource.get("metadata", {}).get("name", "unknown")
            ns = resource.get("metadata", {}).get("namespace", namespace)

            # Ensure metadata and namespace are present
            if "metadata" not in resource:
                resource["metadata"] = {}
            if "namespace" not in resource["metadata"] and ns:
                resource["metadata"]["namespace"] = ns

            try:
                # Prepare API clients
                v1 = client.CoreV1Api()
                apps_v1 = client.AppsV1Api()
                batch_v1 = client.BatchV1Api()
                networking_v1 = client.NetworkingV1Api()
                rbac_v1 = client.RbacAuthorizationV1Api()
                autoscaling_v2 = client.AutoscalingV2Api()

                # Upsert logic per kind: try read -> patch, on 404 create
                if kind == "Pod":
                    try:
                        v1.read_namespaced_pod(name=name, namespace=ns)
                        v1.patch_namespaced_pod(name=name, namespace=ns, body=resource)
                        results.append(f"~ Pod {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            v1.create_namespaced_pod(namespace=ns, body=resource)
                            results.append(f"✓ Pod {name} created in {ns}")
                        else:
                            results.append(f"✗ Pod {name}: {e.reason}")
                elif kind == "Service":
                    try:
                        v1.read_namespaced_service(name=name, namespace=ns)
                        v1.patch_namespaced_service(name=name, namespace=ns, body=resource)
                        results.append(f"~ Service {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            v1.create_namespaced_service(namespace=ns, body=resource)
                            results.append(f"✓ Service {name} created in {ns}")
                        else:
                            results.append(f"✗ Service {name}: {e.reason}")
                elif kind == "Deployment":
                    try:
                        apps_v1.read_namespaced_deployment(name=name, namespace=ns)
                        apps_v1.patch_namespaced_deployment(name=name, namespace=ns, body=resource)
                        results.append(f"~ Deployment {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            apps_v1.create_namespaced_deployment(namespace=ns, body=resource)
                            results.append(f"✓ Deployment {name} created in {ns}")
                        else:
                            results.append(f"✗ Deployment {name}: {e.reason}")
                elif kind == "StatefulSet":
                    try:
                        apps_v1.read_namespaced_stateful_set(name=name, namespace=ns)
                        apps_v1.patch_namespaced_stateful_set(name=name, namespace=ns, body=resource)
                        results.append(f"~ StatefulSet {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            apps_v1.create_namespaced_stateful_set(namespace=ns, body=resource)
                            results.append(f"✓ StatefulSet {name} created in {ns}")
                        else:
                            results.append(f"✗ StatefulSet {name}: {e.reason}")
                elif kind == "DaemonSet":
                    try:
                        apps_v1.read_namespaced_daemon_set(name=name, namespace=ns)
                        apps_v1.patch_namespaced_daemon_set(name=name, namespace=ns, body=resource)
                        results.append(f"~ DaemonSet {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            apps_v1.create_namespaced_daemon_set(namespace=ns, body=resource)
                            results.append(f"✓ DaemonSet {name} created in {ns}")
                        else:
                            results.append(f"✗ DaemonSet {name}: {e.reason}")
                elif kind == "ConfigMap":
                    try:
                        v1.read_namespaced_config_map(name=name, namespace=ns)
                        v1.patch_namespaced_config_map(name=name, namespace=ns, body=resource)
                        results.append(f"~ ConfigMap {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            v1.create_namespaced_config_map(namespace=ns, body=resource)
                            results.append(f"✓ ConfigMap {name} created in {ns}")
                        else:
                            results.append(f"✗ ConfigMap {name}: {e.reason}")
                elif kind == "Secret":
                    try:
                        v1.read_namespaced_secret(name=name, namespace=ns)
                        v1.patch_namespaced_secret(name=name, namespace=ns, body=resource)
                        results.append(f"~ Secret {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            v1.create_namespaced_secret(namespace=ns, body=resource)
                            results.append(f"✓ Secret {name} created in {ns}")
                        else:
                            results.append(f"✗ Secret {name}: {e.reason}")
                elif kind in ["PersistentVolumeClaim", "PersistentVolumeClaim".lower()]:
                    try:
                        v1.read_namespaced_persistent_volume_claim(name=name, namespace=ns)
                        v1.patch_namespaced_persistent_volume_claim(name=name, namespace=ns, body=resource)
                        results.append(f"~ PVC {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            v1.create_namespaced_persistent_volume_claim(namespace=ns, body=resource)
                            results.append(f"✓ PVC {name} created in {ns}")
                        else:
                            results.append(f"✗ PVC {name}: {e.reason}")
                elif kind == "PersistentVolume":
                    try:
                        v1.read_persistent_volume(name=name)
                        v1.patch_persistent_volume(name=name, body=resource)
                        results.append(f"~ PV {name} patched")
                    except ApiException as e:
                        if e.status == 404:
                            v1.create_persistent_volume(body=resource)
                            results.append(f"✓ PV {name} created")
                        else:
                            results.append(f"✗ PV {name}: {e.reason}")
                elif kind == "Ingress":
                    try:
                        networking_v1.read_namespaced_ingress(name=name, namespace=ns)
                        networking_v1.patch_namespaced_ingress(name=name, namespace=ns, body=resource)
                        results.append(f"~ Ingress {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            networking_v1.create_namespaced_ingress(namespace=ns, body=resource)
                            results.append(f"✓ Ingress {name} created in {ns}")
                        else:
                            results.append(f"✗ Ingress {name}: {e.reason}")
                elif kind == "NetworkPolicy":
                    try:
                        networking_v1.read_namespaced_network_policy(name=name, namespace=ns)
                        networking_v1.patch_namespaced_network_policy(name=name, namespace=ns, body=resource)
                        results.append(f"~ NetworkPolicy {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            networking_v1.create_namespaced_network_policy(namespace=ns, body=resource)
                            results.append(f"✓ NetworkPolicy {name} created in {ns}")
                        else:
                            results.append(f"✗ NetworkPolicy {name}: {e.reason}")
                elif kind == "Role":
                    try:
                        rbac_v1.read_namespaced_role(name=name, namespace=ns)
                        rbac_v1.patch_namespaced_role(name=name, namespace=ns, body=resource)
                        results.append(f"~ Role {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            rbac_v1.create_namespaced_role(namespace=ns, body=resource)
                            results.append(f"✓ Role {name} created in {ns}")
                        else:
                            results.append(f"✗ Role {name}: {e.reason}")
                elif kind == "RoleBinding":
                    try:
                        rbac_v1.read_namespaced_role_binding(name=name, namespace=ns)
                        rbac_v1.patch_namespaced_role_binding(name=name, namespace=ns, body=resource)
                        results.append(f"~ RoleBinding {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            rbac_v1.create_namespaced_role_binding(namespace=ns, body=resource)
                            results.append(f"✓ RoleBinding {name} created in {ns}")
                        else:
                            results.append(f"✗ RoleBinding {name}: {e.reason}")
                elif kind == "ClusterRole":
                    try:
                        rbac_v1.read_cluster_role(name=name)
                        rbac_v1.patch_cluster_role(name=name, body=resource)
                        results.append(f"~ ClusterRole {name} patched")
                    except ApiException as e:
                        if e.status == 404:
                            rbac_v1.create_cluster_role(body=resource)
                            results.append(f"✓ ClusterRole {name} created")
                        else:
                            results.append(f"✗ ClusterRole {name}: {e.reason}")
                elif kind == "ClusterRoleBinding":
                    try:
                        rbac_v1.read_cluster_role_binding(name=name)
                        rbac_v1.patch_cluster_role_binding(name=name, body=resource)
                        results.append(f"~ ClusterRoleBinding {name} patched")
                    except ApiException as e:
                        if e.status == 404:
                            rbac_v1.create_cluster_role_binding(body=resource)
                            results.append(f"✓ ClusterRoleBinding {name} created")
                        else:
                            results.append(f"✗ ClusterRoleBinding {name}: {e.reason}")
                elif kind == "ServiceAccount":
                    try:
                        v1.read_namespaced_service_account(name=name, namespace=ns)
                        v1.patch_namespaced_service_account(name=name, namespace=ns, body=resource)
                        results.append(f"~ ServiceAccount {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            v1.create_namespaced_service_account(namespace=ns, body=resource)
                            results.append(f"✓ ServiceAccount {name} created in {ns}")
                        else:
                            results.append(f"✗ ServiceAccount {name}: {e.reason}")
                elif kind == "Namespace":
                    try:
                        v1.read_namespace(name=name)
                        v1.patch_namespace(name=name, body=resource)
                        results.append(f"~ Namespace {name} patched")
                    except ApiException as e:
                        if e.status == 404:
                            v1.create_namespace(body=resource)
                            results.append(f"✓ Namespace {name} created")
                        else:
                            results.append(f"✗ Namespace {name}: {e.reason}")
                elif kind in ["HorizontalPodAutoscaler", "Horizontalpodautoscaler", "hpa"]:
                    try:
                        autoscaling_v2.read_namespaced_horizontal_pod_autoscaler(name=name, namespace=ns)
                        autoscaling_v2.patch_namespaced_horizontal_pod_autoscaler(name=name, namespace=ns, body=resource)
                        results.append(f"~ HPA {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            autoscaling_v2.create_namespaced_horizontal_pod_autoscaler(namespace=ns, body=resource)
                            results.append(f"✓ HPA {name} created in {ns}")
                        else:
                            results.append(f"✗ HPA {name}: {e.reason}")
                elif kind == "Job":
                    try:
                        batch_v1.read_namespaced_job(name=name, namespace=ns)
                        batch_v1.patch_namespaced_job(name=name, namespace=ns, body=resource)
                        results.append(f"~ Job {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            batch_v1.create_namespaced_job(namespace=ns, body=resource)
                            results.append(f"✓ Job {name} created in {ns}")
                        else:
                            results.append(f"✗ Job {name}: {e.reason}")
                elif kind == "CronJob":
                    try:
                        batch_v1.read_namespaced_cron_job(name=name, namespace=ns)
                        batch_v1.patch_namespaced_cron_job(name=name, namespace=ns, body=resource)
                        results.append(f"~ CronJob {name} patched in {ns}")
                    except ApiException as e:
                        if e.status == 404:
                            batch_v1.create_namespaced_cron_job(namespace=ns, body=resource)
                            results.append(f"✓ CronJob {name} created in {ns}")
                        else:
                            results.append(f"✗ CronJob {name}: {e.reason}")
                else:
                    results.append(f"⚠ {kind} {name}: Unsupported resource type")
                    continue

            except ApiException as e:
                # Specific API errors
                if getattr(e, "status", None) == 409:
                    results.append(f"⚠ {kind} {name}: Already exists")
                else:
                    results.append(f"✗ {kind} {name}: {getattr(e, 'reason', str(e))}")
            except Exception as e:
                results.append(f"✗ {kind} {name}: {str(e)}")

        return "\n".join(results) if results else "No resources to apply"
    except Exception as e:
        return f"Error parsing YAML: {e}"


@mcp.tool()
def generate_deployment_yaml(name: str, namespace: str = "default", image: str = "nginx:latest", replicas: int = 1, port: int = 80, labels: Optional[Dict[str, str]] = None) -> str:
    """
    Create a Deployment resource from parameters.
    
    Args:
        name (str): Name of the deployment
        namespace (str): Namespace. Default is "default".
        image (str): Container image. Default is "nginx:latest".
        replicas (int): Number of replicas. Default is 1.
        port (int): Container port. Default is 80.
        labels (dict): Labels for the deployment. Default is None.
    
    Returns:
        str: Created deployment resource as JSON
    """
    if labels is None:
        labels = {"app": name}
    
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": labels
        },
        "spec": {
            "replicas": replicas,
            "selector": {
                "matchLabels": {"app": name}
            },
            "template": {
                "metadata": {
                    "labels": {"app": name}
                },
                "spec": {
                    "containers": [
                        {
                            "name": name,
                            "image": image,
                            "ports": [{"containerPort": port}]
                        }
                    ]
                }
            }
        }
    }
    return json.dumps(deployment, indent=2)


@mcp.tool()
def generate_service_yaml(name: str, namespace: str = "default", app_label: str = None, port: int = 80, target_port: int = 80, service_type: str = "ClusterIP") -> str:
    """
    Create a Service resource from parameters.
    
    Args:
        name (str): Name of the service
        namespace (str): Namespace. Default is "default".
        app_label (str): App label to select pods. Default is service name.
        port (int): Service port. Default is 80.
        target_port (int): Container port. Default is 80.
        service_type (str): Service type (ClusterIP, NodePort, LoadBalancer). Default is "ClusterIP".
    
    Returns:
        str: Created service resource as JSON
    """
    if app_label is None:
        app_label = name
    
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "type": service_type,
            "selector": {"app": app_label},
            "ports": [
                {
                    "port": port,
                    "targetPort": target_port,
                    "protocol": "TCP"
                }
            ]
        }
    }
    return json.dumps(service, indent=2)


@mcp.tool()
def generate_configmap_yaml(name: str, namespace: str = "default", data: Optional[Dict[str, str]] = None) -> str:
    """
    Create a ConfigMap resource from parameters.
    
    Args:
        name (str): Name of the ConfigMap
        namespace (str): Namespace. Default is "default".
        data (dict): Key-value pairs for the ConfigMap. Default is None.
    
    Returns:
        str: Created ConfigMap resource as JSON
    """
    if data is None:
        data = {"config.txt": "example=value"}
    
    configmap = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "data": data
    }
    return json.dumps(configmap, indent=2)


@mcp.tool()
def generate_secret_yaml(name: str, namespace: str = "default", secret_type: str = "Opaque", data: Optional[Dict[str, str]] = None) -> str:
    """
    Create a Secret resource from parameters.
    
    Args:
        name (str): Name of the Secret
        namespace (str): Namespace. Default is "default".
        secret_type (str): Secret type (Opaque, kubernetes.io/basic-auth, etc.). Default is "Opaque".
        data (dict): Key-value pairs (will be base64 encoded). Default is None.
    
    Returns:
        str: Created Secret resource as JSON
    """
    import base64
    
    if data is None:
        data = {"username": "admin", "password": "secret"}
    
    # Base64 encode the data
    encoded_data = {k: base64.b64encode(v.encode()).decode() for k, v in data.items()}
    
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "type": secret_type,
        "data": encoded_data
    }
    return json.dumps(secret, indent=2)


@mcp.tool()
def generate_ingress_yaml(name: str, namespace: str = "default", host: str = "example.com", service_name: str = None, service_port: int = 80) -> str:
    """
    Create an Ingress resource from parameters.
    
    Args:
        name (str): Name of the Ingress
        namespace (str): Namespace. Default is "default".
        host (str): Hostname for the ingress. Default is "example.com".
        service_name (str): Backend service name. Default is ingress name.
        service_port (int): Backend service port. Default is 80.
    
    Returns:
        str: Created Ingress resource as JSON
    """
    if service_name is None:
        service_name = name
    
    ingress = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "rules": [
                {
                    "host": host,
                    "http": {
                        "paths": [
                            {
                                "path": "/",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": service_name,
                                        "port": {"number": service_port}
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }
    return json.dumps(ingress, indent=2)


@mcp.tool()
def generate_pvc_yaml(name: str, namespace: str = "default", size: str = "10Gi", storage_class: str = "standard", access_mode: str = "ReadWriteOnce") -> str:
    """
    Create a PersistentVolumeClaim resource from parameters.
    
    Args:
        name (str): Name of the PVC
        namespace (str): Namespace. Default is "default".
        size (str): Storage size. Default is "10Gi".
        storage_class (str): Storage class name. Default is "standard".
        access_mode (str): Access mode (ReadWriteOnce, ReadOnlyMany, ReadWriteMany). Default is "ReadWriteOnce".
    
    Returns:
        str: Created PVC resource as JSON
    """
    pvc = {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "accessModes": [access_mode],
            "storageClassName": storage_class,
            "resources": {
                "requests": {
                    "storage": size
                }
            }
        }
    }
    return json.dumps(pvc, indent=2)


@mcp.tool()
def generate_hpa_yaml(name: str, namespace: str = "default", deployment: str = None, min_replicas: int = 1, max_replicas: int = 10, cpu_percent: int = 80) -> str:
    """
    Create a HorizontalPodAutoscaler resource from parameters.
    
    Args:
        name (str): Name of the HPA
        namespace (str): Namespace. Default is "default".
        deployment (str): Target deployment name. Default is HPA name.
        min_replicas (int): Minimum replicas. Default is 1.
        max_replicas (int): Maximum replicas. Default is 10.
        cpu_percent (int): CPU utilization threshold. Default is 80.
    
    Returns:
        str: Created HPA resource as JSON
    """
    if deployment is None:
        deployment = name
    
    hpa = {
        "apiVersion": "autoscaling/v2",
        "kind": "HorizontalPodAutoscaler",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "scaleTargetRef": {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "name": deployment
            },
            "minReplicas": min_replicas,
            "maxReplicas": max_replicas,
            "metrics": [
                {
                    "type": "Resource",
                    "resource": {
                        "name": "cpu",
                        "target": {
                            "type": "Utilization",
                            "averageUtilization": cpu_percent
                        }
                    }
                }
            ]
        }
    }
    return json.dumps(hpa, indent=2)


@mcp.tool()
def generate_job_yaml(name: str, namespace: str = "default", image: str = "busybox:latest", command: Optional[List[str]] = None) -> str:
    """
    Create a Job resource from parameters.
    
    Args:
        name (str): Name of the Job
        namespace (str): Namespace. Default is "default".
        image (str): Container image. Default is "busybox:latest".
        command (list): Command to run. Default is ["echo", "hello"].
    
    Returns:
        str: Created Job resource as JSON
    """
    if command is None:
        command = ["echo", "hello"]
    
    job = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": name,
                            "image": image,
                            "command": command
                        }
                    ],
                    "restartPolicy": "Never"
                }
            }
        }
    }
    return json.dumps(job, indent=2)


@mcp.tool()
def generate_cronjob_yaml(name: str, namespace: str = "default", schedule: str = "0 0 * * *", image: str = "busybox:latest", command: Optional[List[str]] = None) -> str:
    """
    Create a CronJob resource from parameters.
    
    Args:
        name (str): Name of the CronJob
        namespace (str): Namespace. Default is "default".
        schedule (str): Cron schedule expression. Default is "0 0 * * *" (daily at midnight).
        image (str): Container image. Default is "busybox:latest".
        command (list): Command to run. Default is ["echo", "hello"].
    
    Returns:
        str: Created CronJob resource as JSON
    """
    if command is None:
        command = ["echo", "hello"]
    
    cronjob = {
        "apiVersion": "batch/v1",
        "kind": "CronJob",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "schedule": schedule,
            "jobTemplate": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": name,
                                    "image": image,
                                    "command": command
                                }
                            ],
                            "restartPolicy": "OnFailure"
                        }
                    }
                }
            }
        }
    }
    return json.dumps(cronjob, indent=2)


@mcp.tool()
def generate_statefulset_yaml(name: str, namespace: str = "default", image: str = "nginx:latest", replicas: int = 1, port: int = 80) -> str:
    """
    Create a StatefulSet resource from parameters.
    
    Args:
        name (str): Name of the StatefulSet
        namespace (str): Namespace. Default is "default".
        image (str): Container image. Default is "nginx:latest".
        replicas (int): Number of replicas. Default is 1.
        port (int): Container port. Default is 80.
    
    Returns:
        str: Created StatefulSet resource as JSON
    """
    statefulset = {
        "apiVersion": "apps/v1",
        "kind": "StatefulSet",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "serviceName": f"{name}-service",
            "replicas": replicas,
            "selector": {
                "matchLabels": {"app": name}
            },
            "template": {
                "metadata": {
                    "labels": {"app": name}
                },
                "spec": {
                    "containers": [
                        {
                            "name": name,
                            "image": image,
                            "ports": [{"containerPort": port}]
                        }
                    ]
                }
            }
        }
    }
    return json.dumps(statefulset, indent=2)


@mcp.tool()
def list_resources(resource_type: str, namespace: str = "default", output_format: str = "table", all_namespaces: bool = False, label_selector: Optional[str] = None, field_selector: Optional[str] = None) -> str:
    """
    Generic tool to list any Kubernetes resource type.
    
    Args:
        resource_type (str): Type of resource (pod, deployment, service, configmap, secret, ingress, job, cronjob, pvc, hpa, statefulset, daemonset, storageclass, etc.)
        namespace (str): Namespace to list from. Default is "default".
        output_format (str): Output format: "table", "json", "yaml", "wide". Default is "table".
        all_namespaces (bool): List from all namespaces. Default is False.
        label_selector (str): Label selector filter. Default is None.
        field_selector (str): Field selector filter. Default is None.
    
    Returns:
        str: List of resources
    """
    resource_type = resource_type.lower().strip()
    
    try:
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        batch_v1 = client.BatchV1Api()
        networking_v1 = client.NetworkingV1Api()
        rbac_v1 = client.RbacAuthorizationV1Api()
        autoscaling_v2 = client.AutoscalingV2Api()
        storage_v1 = client.StorageV1Api()
        custom_api = client.CustomObjectsApi()
        
        resources = None
        
        # Core API resources
        if resource_type in ["pod", "pods"]:
            if all_namespaces:
                resources = v1.list_pod_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = v1.list_namespaced_pod(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["service", "services", "svc"]:
            if all_namespaces:
                resources = v1.list_service_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = v1.list_namespaced_service(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["configmap", "configmaps", "cm"]:
            if all_namespaces:
                resources = v1.list_config_map_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = v1.list_namespaced_config_map(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["secret", "secrets"]:
            if all_namespaces:
                resources = v1.list_secret_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = v1.list_namespaced_secret(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["persistentvolumeclaim", "pvc", "pvcs"]:
            if all_namespaces:
                resources = v1.list_persistent_volume_claim_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = v1.list_namespaced_persistent_volume_claim(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["persistentvolume", "pv", "pvs"]:
            resources = v1.list_persistent_volume(label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["namespace", "namespaces", "ns"]:
            resources = v1.list_namespace(label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["node", "nodes"]:
            resources = v1.list_node(label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["serviceaccount", "serviceaccounts", "sa"]:
            if all_namespaces:
                resources = v1.list_service_account_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = v1.list_namespaced_service_account(namespace, label_selector=label_selector, field_selector=field_selector)
        
        # Apps API resources
        elif resource_type in ["deployment", "deployments", "deploy"]:
            if all_namespaces:
                resources = apps_v1.list_deployment_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = apps_v1.list_namespaced_deployment(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["statefulset", "statefulsets", "sts"]:
            if all_namespaces:
                resources = apps_v1.list_stateful_set_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = apps_v1.list_namespaced_stateful_set(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["daemonset", "daemonsets", "ds"]:
            if all_namespaces:
                resources = apps_v1.list_daemon_set_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = apps_v1.list_namespaced_daemon_set(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["replicaset", "replicasets", "rs"]:
            if all_namespaces:
                resources = apps_v1.list_replica_set_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = apps_v1.list_namespaced_replica_set(namespace, label_selector=label_selector, field_selector=field_selector)
        
        # Batch API resources
        elif resource_type in ["job", "jobs"]:
            if all_namespaces:
                resources = batch_v1.list_job_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = batch_v1.list_namespaced_job(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["cronjob", "cronjobs", "cj"]:
            if all_namespaces:
                resources = batch_v1.list_cron_job_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = batch_v1.list_namespaced_cron_job(namespace, label_selector=label_selector, field_selector=field_selector)
        
        # Networking API resources
        elif resource_type in ["ingress", "ingresses", "ing"]:
            if all_namespaces:
                resources = networking_v1.list_ingress_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = networking_v1.list_namespaced_ingress(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["networkpolicy", "networkpolicies", "netpol"]:
            if all_namespaces:
                resources = networking_v1.list_network_policy_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = networking_v1.list_namespaced_network_policy(namespace, label_selector=label_selector, field_selector=field_selector)
        
        # RBAC API resources
        elif resource_type in ["role", "roles"]:
            if all_namespaces:
                resources = rbac_v1.list_role_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = rbac_v1.list_namespaced_role(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["rolebinding", "rolebindings", "rb"]:
            if all_namespaces:
                resources = rbac_v1.list_role_binding_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = rbac_v1.list_namespaced_role_binding(namespace, label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["clusterrole", "clusterroles", "cr"]:
            resources = rbac_v1.list_cluster_role(label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["clusterrolebinding", "clusterrolebindings", "crb"]:
            resources = rbac_v1.list_cluster_role_binding(label_selector=label_selector, field_selector=field_selector)
        
        # Autoscaling API resources
        elif resource_type in ["hpa", "horizontalpodautoscaler", "horizontalpodautoscalers"]:
            if all_namespaces:
                resources = autoscaling_v2.list_horizontal_pod_autoscaler_for_all_namespaces(label_selector=label_selector, field_selector=field_selector)
            else:
                resources = autoscaling_v2.list_namespaced_horizontal_pod_autoscaler(namespace, label_selector=label_selector, field_selector=field_selector)
        
        # Storage API resources
        elif resource_type in ["storageclass", "storageclasses", "sc"]:
            resources = storage_v1.list_storage_class(label_selector=label_selector, field_selector=field_selector)
        elif resource_type in ["volumeattachment", "volumeattachments", "va"]:
            resources = storage_v1.list_volume_attachment(label_selector=label_selector, field_selector=field_selector)
        
        else:
            return f"❌ Unknown resource type: {resource_type}\n\n📚 Supported resource types:\n- pod, deployment, service, configmap, secret, ingress, job, cronjob\n- pvc, hpa, statefulset, daemonset, role, rolebinding, clusterrole\n- clusterrolebinding, node, namespace, serviceaccount, storageclass, volumeattachment\n\nShort names: svc, deploy, sts, ds, cm, rb, cr, crb, sa, sc, va, etc."
        
        if resources is None:
            return f"No resources found for type: {resource_type}"
        
        # Format output
        if output_format == "json":
            resource_list = [r.to_dict() for r in resources.items]
            return json.dumps(resource_list, indent=2)
        elif output_format == "yaml":
            import yaml
            resource_list = [r.to_dict() for r in resources.items]
            return yaml.dump(resource_list, default_flow_style=False)
        else:  # table format (default)
            headers = "NAME\tNAMESPACE\tAGE\n"
            output = headers
            for resource in resources.items:
                name = resource.metadata.name
                ns = getattr(resource.metadata, "namespace", None) or "N/A"
                age = (datetime.datetime.now(datetime.timezone.utc) - resource.metadata.creation_timestamp).seconds // 60
                output += f"{name}\t{ns}\t{age}m\n"
            return output
    
    except Exception as e:
        return f"❌ Error listing resources: {str(e)}"


@mcp.tool()
def patch_storageclass(storageclass_name: str, patch_data: Dict[str, Any] = None) -> str:
    """
    Patch a StorageClass resource.
    
    Args:
        storageclass_name (str): Name of the StorageClass
        patch_data (dict): Patch data to apply (JSON format)
    
    Returns:
        str: Patch status
    """
    storage_v1 = client.StorageV1Api()
    try:
        if patch_data is None:
            patch_data = {}
        storage_v1.patch_storage_class(name=storageclass_name, body=patch_data)
        return f"✓ StorageClass {storageclass_name} patched successfully."
    except Exception as e:
        return f"✗ Error patching StorageClass: {e}"


@mcp.tool()
def delete_resource(resource_type: str, resource_name: str, namespace: str = "default", force: bool = False, grace_period: int = 30) -> str:
    """
    Generic tool to delete any Kubernetes resource.
    
    Args:
        resource_type (str): Type of resource (pod, deployment, service, storageclass, etc.)
        resource_name (str): Name of the resource
        namespace (str): Namespace. Default is "default".
        force (bool): Force delete. Default is False.
        grace_period (int): Grace period in seconds. Default is 30.
    
    Returns:
        str: Deletion status
    """
    resource_type = resource_type.lower().strip()
    
    try:
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        batch_v1 = client.BatchV1Api()
        networking_v1 = client.NetworkingV1Api()
        rbac_v1 = client.RbacAuthorizationV1Api()
        autoscaling_v2 = client.AutoscalingV2Api()
        storage_v1 = client.StorageV1Api()
        
        propagation_policy = "Foreground" if force else "Background"
        
        # Core API resources
        if resource_type in ["pod", "pods"]:
            v1.delete_namespaced_pod(name=resource_name, namespace=namespace, grace_period_seconds=grace_period, propagation_policy=propagation_policy)
        elif resource_type in ["service", "services", "svc"]:
            v1.delete_namespaced_service(name=resource_name, namespace=namespace)
        elif resource_type in ["configmap", "configmaps", "cm"]:
            v1.delete_namespaced_config_map(name=resource_name, namespace=namespace)
        elif resource_type in ["secret", "secrets"]:
            v1.delete_namespaced_secret(name=resource_name, namespace=namespace)
        elif resource_type in ["persistentvolumeclaim", "pvc", "pvcs"]:
            v1.delete_namespaced_persistent_volume_claim(name=resource_name, namespace=namespace)
        elif resource_type in ["persistentvolume", "pv", "pvs"]:
            v1.delete_persistent_volume(name=resource_name)
        elif resource_type in ["namespace", "namespaces", "ns"]:
            v1.delete_namespace(name=resource_name)
        elif resource_type in ["serviceaccount", "serviceaccounts", "sa"]:
            v1.delete_namespaced_service_account(name=resource_name, namespace=namespace)
        
        # Apps API resources
        elif resource_type in ["deployment", "deployments", "deploy"]:
            apps_v1.delete_namespaced_deployment(name=resource_name, namespace=namespace, propagation_policy=propagation_policy)
        elif resource_type in ["statefulset", "statefulsets", "sts"]:
            apps_v1.delete_namespaced_stateful_set(name=resource_name, namespace=namespace, propagation_policy=propagation_policy)
        elif resource_type in ["daemonset", "daemonsets", "ds"]:
            apps_v1.delete_namespaced_daemon_set(name=resource_name, namespace=namespace, propagation_policy=propagation_policy)
        elif resource_type in ["replicaset", "replicasets", "rs"]:
            apps_v1.delete_namespaced_replica_set(name=resource_name, namespace=namespace, propagation_policy=propagation_policy)
        
        # Batch API resources
        elif resource_type in ["job", "jobs"]:
            batch_v1.delete_namespaced_job(name=resource_name, namespace=namespace, propagation_policy=propagation_policy)
        elif resource_type in ["cronjob", "cronjobs", "cj"]:
            batch_v1.delete_namespaced_cron_job(name=resource_name, namespace=namespace, propagation_policy=propagation_policy)
        
        # Networking API resources
        elif resource_type in ["ingress", "ingresses", "ing"]:
            networking_v1.delete_namespaced_ingress(name=resource_name, namespace=namespace)
        elif resource_type in ["networkpolicy", "networkpolicies", "netpol"]:
            networking_v1.delete_namespaced_network_policy(name=resource_name, namespace=namespace)
        
        # RBAC API resources
        elif resource_type in ["role", "roles"]:
            rbac_v1.delete_namespaced_role(name=resource_name, namespace=namespace)
        elif resource_type in ["rolebinding", "rolebindings", "rb"]:
            rbac_v1.delete_namespaced_role_binding(name=resource_name, namespace=namespace)
        elif resource_type in ["clusterrole", "clusterroles", "cr"]:
            rbac_v1.delete_cluster_role(name=resource_name)
        elif resource_type in ["clusterrolebinding", "clusterrolebindings", "crb"]:
            rbac_v1.delete_cluster_role_binding(name=resource_name)
        
        # Autoscaling API resources
        elif resource_type in ["hpa", "horizontalpodautoscaler", "horizontalpodautoscalers"]:
            autoscaling_v2.delete_namespaced_horizontal_pod_autoscaler(name=resource_name, namespace=namespace)
        
        # Storage API resources
        elif resource_type in ["storageclass", "storageclasses", "sc"]:
            storage_v1.delete_storage_class(name=resource_name)
        elif resource_type in ["volumeattachment", "volumeattachments", "va"]:
            storage_v1.delete_volume_attachment(name=resource_name)
        
        else:
            return f"❌ Unknown resource type: {resource_type}"
        
        return f"✓ {resource_type} '{resource_name}' deleted successfully."
    except ApiException as e:
        if e.status == 404:
            return f"⚠ {resource_type} '{resource_name}' not found."
        return f"✗ Error deleting {resource_type}: {e.reason}"
    except Exception as e:
        return f"✗ Error deleting resource: {e}"


def main():
    """Initialize and run the MCP server with streamable HTTP transport."""
    print("Starting K8s MCP Server...")
    print("\n📋 Generic Listing & Deletion Tools:")
    print("  - list_resources: List any resource type (pod, deployment, service, storageclass, etc.)")
    print("  - delete_resource: Delete any resource type")
    print("\n🔧 Resource-Specific Patch Tools:")
    print("  - patch_pod, patch_deployment, patch_service, patch_configmap")
    print("  - patch_secret, patch_statefulset, patch_daemonset, patch_ingress")
    print("  - patch_hpa, patch_storageclass")
    print("\n🔨 YAML Generation Tools:")
    print("  - apply_yaml: Apply YAML content to cluster")
    print("  - generate_deployment_yaml, generate_service_yaml, generate_configmap_yaml")
    print("  - generate_secret_yaml, generate_ingress_yaml, generate_pvc_yaml")
    print("  - generate_hpa_yaml, generate_job_yaml, generate_cronjob_yaml, generate_statefulset_yaml")
    print("\n📊 Supported resource types for list/delete:")
    print("  pod, deployment, service, configmap, secret, ingress, job, cronjob")
    print("  pvc, hpa, statefulset, daemonset, role, rolebinding, clusterrole")
    print("  clusterrolebinding, node, namespace, serviceaccount, storageclass, volumeattachment")
    print("\nServer will be available at http://localhost:8000")
    print("SSE endpoint: http://localhost:8000/sse")
    
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
