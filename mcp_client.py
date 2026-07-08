import os
import sys
import warnings

# Suppress Pydantic deprecation warnings early
os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")

import asyncio
import json
import re
import sqlite3
from typing import List, Dict, Any

from fastmcp import Client
from google import genai
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.markdown import Markdown
from rich.console import Group

GENI_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GENI_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set")

console = Console()

class GeminiMCPClient:
    
    def __init__(self, 
                 mcp_server_url: str = "http://localhost:8000/sse",
                 model: str = "gemma-4-31b-it",
                 api_key: str = ""):
        self.mcp_server_url = mcp_server_url
        self.model_name = model
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
        self.client = genai.Client(api_key=self.api_key)
        
        self.mcp_client = None
        self.available_tools = []
        self.conversation_history = []
        
        self.chat_lock = asyncio.Lock()
        self.active_watches = {}
        
        self.db_path = os.path.expanduser('~/.mcp_k8s_session.db')
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database and load existing history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS history 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           role TEXT, 
                           parts_json TEXT)''')
            
            cursor = conn.execute("SELECT role, parts_json FROM history ORDER BY id ASC")
            for row in cursor:
                self.conversation_history.append({
                    'role': row[0],
                    'parts': json.loads(row[1])
                })
                
    def _add_to_history(self, role: str, parts: List[Dict]):
        """Append to in-memory history and persist to SQLite."""
        self.conversation_history.append({'role': role, 'parts': parts})
        
        safe_parts = []
        for p in parts:
            if 'function_call' in p:
                fc = p['function_call']
                if hasattr(fc, 'model_dump'):
                    safe_fc = fc.model_dump()
                elif hasattr(fc, 'name') and hasattr(fc, 'args'):
                    safe_fc = {'name': fc.name, 'args': dict(fc.args)}
                else:
                    safe_fc = str(fc)
                safe_parts.append({'function_call': safe_fc})
            else:
                safe_parts.append(p)
                
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history (role, parts_json) VALUES (?, ?)", 
                         (role, json.dumps(safe_parts)))

    def _clean_schema_for_gemini(self, schema: Dict) -> Dict:
        """Remove Gemini-incompatible fields from schema."""
        if not isinstance(schema, dict):
            return schema
        
        cleaned = {}
        
        for key, value in schema.items():
            if key in ['additional_properties', 'additionalProperties', 'anyOf', 'any_of', 'allOf', 'all_of', 'oneOf', 'one_of']:
                continue
            
            if isinstance(value, dict):
                cleaned[key] = self._clean_schema_for_gemini(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    self._clean_schema_for_gemini(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned[key] = value
        
        return cleaned

    async def connect(self):
        """Connect to the MCP server and discover available tools."""
        try:
            self.mcp_client = Client(self.mcp_server_url)
            await self.mcp_client.__aenter__()
            
            tools_response = await self.mcp_client.list_tools()
            self.available_tools = tools_response
            
            console.print(f"[bold green]✓[/bold green] Connected to {self.mcp_server_url}")
            console.print(f"[bold green]✓[/bold green] Found {len(self.available_tools)} tools:")
            for tool in self.available_tools:
                console.print(f"  • [cyan]{tool.name}[/cyan]")
            print()
        except Exception as e:
            console.print(f"[bold red]Failed to connect to MCP Server:[/bold red] {e}")
            raise
        
    async def disconnect(self):
        """Clean up connections."""
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)
        
        # Close genai client session to prevent 'Unclosed client session' warning
        if hasattr(self, 'client'):
            try:
                # The genai SDK creates an aiohttp session for the async client
                if hasattr(self.client, 'aio') and hasattr(self.client.aio, 'close'):
                    # Some versions have close() on aio, some don't
                    await self.client.aio.close()
                elif hasattr(self.client, 'close'):
                    self.client.close()
            except Exception:
                pass
    
    def _format_tools_for_gemini(self) -> List[Dict]:
        """Convert MCP tools to Gemini format."""
        gemini_tools = []
        
        for tool in self.available_tools:
            properties = {}
            required = []
            
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                schema = tool.inputSchema
                raw_properties = schema.get('properties', {})
                required = schema.get('required', [])
                
                for prop_name, prop_schema in raw_properties.items():
                    properties[prop_name] = self._clean_schema_for_gemini(prop_schema)
            
            gemini_tools.append({
                'function_declarations': [{
                    'name': tool.name,
                    'description': tool.description or f"Execute {tool.name}",
                    'parameters': {
                        'type': 'OBJECT',
                        'properties': properties,
                        'required': required
                    }
                }]
            })
        
        return gemini_tools
    
    def _create_system_instruction(self) -> str:
        return """You are a Senior DevOps Engineer and CKA (Certified Kubernetes Administrator) certified expert assistant working in a CRITICAL PRODUCTION ENVIRONMENT.

        PERSONA & EXPERTISE:
        - Senior DevOps Engineer with 10+ years of experience in cloud-native technologies
        - CKA Certified Kubernetes Administrator with deep understanding of K8s internals
        - Expert in production-grade deployments, high availability, and disaster recovery
        - Strong background in security best practices, RBAC, and compliance
        - Experienced in multi-cluster management, GitOps, and CI/CD pipelines
        - Proficient in troubleshooting complex distributed systems under pressure

        CRITICAL ENVIRONMENT PROTOCOLS:
        ⚠️ PRODUCTION SYSTEM - Exercise extreme caution with all operations
        - Always verify namespace, cluster context, and resource names before operations
        - Never perform destructive operations without explicit user confirmation
        - Prioritize system stability and minimize downtime
        - Flag any high-risk operations (deletions, scaling, restarts) with clear warnings
        - Assume zero-downtime requirements unless stated otherwise

        OPERATIONAL RULES:
        1. Tool Usage:
           - Only call K8s tools when user requests specific cluster information
           - For greetings/general questions, respond directly WITHOUT tools
           - Call multiple tools if needed for comprehensive analysis
           - Always validate tool results before presenting to user

        2. Response Format:
           - Provide clear, professionally formatted responses
           - Use tables for structured data (pods, deployments, services)
           - Include relevant metrics (CPU, memory, replicas, age)
           - Highlight anomalies, errors, or potential issues
           - Add actionable recommendations when problems detected

        3. Communication Style:
           - Professional, concise, and technically accurate
           - Use industry-standard terminology
           - Explain complex concepts clearly when needed
           - Proactively warn about risks and implications
           - Suggest best practices aligned with production standards

        4. Decision Framework:
           - Does this query require cluster data? → Use tools
           - Is this a destructive operation? → Request confirmation + warn
           - Is this a general question? → Respond directly with expertise
           - Is there ambiguity? → Ask clarifying questions before acting

        5. Change Verification Protocol:
           - After ANY create/update/delete operation, ALWAYS verify the change
           - Use appropriate kubectl get/describe commands to confirm resource state
           - Check that pods are running, services are ready, and configurations are applied
           - Verify rollout status for deployments and statefulsets
           - Report back to user with confirmation that changes are live and healthy
           - If verification fails, immediately alert user and provide troubleshooting steps

        SECURITY & COMPLIANCE:
        - Never expose sensitive data (secrets, tokens, passwords)
        - Respect RBAC policies and namespace boundaries
        - Assume all environments are production unless specified as dev/test
        - Follow principle of least privilege

        Think before acting: Does this require tools? What's the risk level? How can I provide maximum value safely?
        
        CRITICAL FORMATTING INSTRUCTION:
        You MUST structure your response exactly like this:
        THINKING:
        (Your internal thought process, reasoning, and planning here)
        RESPONSE:
        (Your final user-facing response here)
        
        Always include both THINKING: and RESPONSE: prefixes."""
    
    def _preprocess_response(self, text: str) -> str:
        """Fix common LaTeX/symbol issues before rendering as Markdown."""
        # LaTeX arrow replacements
        replacements = {
            r'$\rightarrow$': '→',
            r'$\leftarrow$': '←',
            r'$\Rightarrow$': '⇒',
            r'$\Leftarrow$': '⇐',
            r'$\leftrightarrow$': '↔',
            r'$\times$': '×',
            r'$\geq$': '≥',
            r'$\leq$': '≤',
            r'$\neq$': '≠',
            r'$\approx$': '≈',
            r'$\infty$': '∞',
        }
        for latex, unicode_char in replacements.items():
            text = text.replace(latex, unicode_char)
        return text
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call an MCP tool."""
        try:
            result = await self.mcp_client.call_tool(tool_name, arguments)
            
            if hasattr(result, 'content') and result.content:
                if isinstance(result.content, list):
                    return '\n'.join([
                        item.text if hasattr(item, 'text') else str(item) 
                        for item in result.content
                    ])
                return str(result.content)
            
            return str(result)
        except Exception as e:
            return f"Error executing tool {tool_name}: {str(e)}"
    
    async def chat_stream(self, user_message: str, max_iterations: int = 10, is_notification: bool = False):
        if is_notification:
            console.print(f"\n[bold yellow]🔔 System Notification:[/bold yellow] {user_message}")
            
        async with self.chat_lock:
            self._add_to_history('user', [{'text': f"System Notification: {user_message}" if is_notification else user_message}])
            
            tools = self._format_tools_for_gemini()
            iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            config = {
                'system_instruction': self._create_system_instruction(),
                'tools': tools if tools else None,
            }
            
            max_api_retries = 3
            api_success = False
            
            for retry_attempt in range(max_api_retries):
                current_text = ""
                function_calls = []
                in_think = False
                think_buffer = ""
                normal_buffer = ""
                api_success = True
                
                try:
                    response = await self.client.aio.models.generate_content_stream(
                        model=self.model_name,
                        contents=self.conversation_history,
                        config=config
                    )
                    
                    use_live = not is_notification
                    
                    if use_live:
                        live_ctx = Live(auto_refresh=True, console=console)
                    else:
                        import contextlib
                        live_ctx = contextlib.nullcontext()

                    with live_ctx as live:
                        renderables = []
                        async for chunk in response:
                            if hasattr(chunk, 'candidates') and chunk.candidates:
                                for candidate in chunk.candidates:
                                    if hasattr(candidate, 'content') and candidate.content:
                                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                            for part in candidate.content.parts:
                                                if hasattr(part, 'text') and part.text:
                                                    text_chunk = part.text
                                                    current_text += text_chunk
                                                    
                                                    if "RESPONSE:" in current_text:
                                                        split = current_text.split("RESPONSE:", 1)
                                                        think_buffer = split[0].replace("THINKING:", "").strip()
                                                        normal_buffer = split[1].strip()
                                                        in_think = False
                                                    else:
                                                        think_buffer = current_text.replace("THINKING:", "").strip()
                                                        normal_buffer = ""
                                                        in_think = True
                                                    
                                                    renderables = []
                                                    if think_buffer:
                                                        think_text = Text(think_buffer, style="dim italic")
                                                        renderables.append(Panel(think_text, title="[dim]💭 Thinking[/dim]", border_style="dim"))
                                                    if normal_buffer:
                                                        renderables.append(Markdown(self._preprocess_response(normal_buffer)))
                                                    
                                                    if renderables and use_live:
                                                        live.update(Group(*renderables))
                                                
                                                if hasattr(part, 'function_call') and part.function_call:
                                                    function_calls.append(part.function_call)
                                                    
                        if not use_live and renderables:
                            console.print(Group(*renderables))
                            
                except Exception as e:
                    error_str = str(e)
                    console.print(f"[red]API Error: {str(e)}[/red]")
                    # Check for typical 5xx indicators
                    if any(code in error_str for code in ["500", "503", "INTERNAL", "UNAVAILABLE"]):
                        console.print(f"\n[bold yellow]API Interrupted ({error_str}), auto-retrying... ({retry_attempt+1}/{max_api_retries})[/bold yellow]")
                        api_success = False
                        await asyncio.sleep(2)
                    else:
                        console.print(f"\n[bold red]Stream Error:[/bold red] {e}")
                        api_success = False
                        break # Unrecoverable, stop retrying
                        
                if api_success:
                    break
            
            if not api_success:
                break # Exit the overall iteration loop if all retries failed

            if not function_calls:
                if current_text:
                    # Only store the RESPONSE part in history, not the THINKING block
                    # This keeps context clean and saves tokens
                    if "RESPONSE:" in current_text:
                        clean_response = current_text.split("RESPONSE:", 1)[1].strip()
                    else:
                        clean_response = current_text.strip()
                    self._add_to_history('model', [{'text': clean_response}])
                break
            
            # Execute function calls
            self._add_to_history('model', [{'function_call': fc} for fc in function_calls])
            
            function_response_parts = []
            for fc in function_calls:
                tool_name = fc.name
                tool_args = dict(fc.args) if hasattr(fc, 'args') else {}
                
                # Call the MCP tool with a clean spinner
                with console.status(f"[cyan]⚙️ Executing tool [bold]{tool_name}[/bold]...[/cyan]"):
                    tool_result = await self._call_mcp_tool(tool_name, tool_args)
                
                # Check for background tasks interception — parse JSON payload from server
                if tool_name == "run_bg_task":
                    try:
                        payload = json.loads(tool_result)
                        bg_tool = payload.get("tool_name", "")
                        bg_args = payload.get("tool_arguments", {})
                    except (json.JSONDecodeError, TypeError):
                        bg_tool = tool_args.get("tool_name", "")
                        bg_args = {}
                    if bg_tool:
                        asyncio.create_task(self._bg_task(bg_tool, bg_args))
                
                elif tool_name == "watch_resource":
                    try:
                        payload = json.loads(tool_result)
                        resource_type = payload.get("resource_type", tool_args.get("resource_type", "pods"))
                        interval = int(payload.get("interval", tool_args.get("interval", 5)))
                        watch_tool_args = {
                            "resource_type": resource_type,
                            "namespace": payload.get("namespace", tool_args.get("namespace", "default")),
                            "interval": interval,
                        }
                    except (json.JSONDecodeError, TypeError):
                        resource_type = tool_args.get("resource_type", "pods")
                        interval = int(tool_args.get("interval", 5))
                        watch_tool_args = tool_args
                    self.active_watches[resource_type] = True
                    asyncio.create_task(self._bg_watch(resource_type, interval, watch_tool_args))
                
                elif tool_name == "stop_watch":
                    resource_type = tool_args.get("resource_type", "pods")
                    self.active_watches[resource_type] = False
                
                # Print a clean, dim completion marker instead of a giant panel
                arg_str = json.dumps(tool_args)
                if len(arg_str) > 60:
                    arg_str = arg_str[:57] + "..."
                
                console.print(f"[dim]  ✓ [cyan]{tool_name}[/cyan]({arg_str}) returned {len(str(tool_result))} chars[/dim]")
                
                # Trim large tool outputs before storing in history
                # Full output was already shown to the user; model only needs a summary
                tool_result_str = str(tool_result)
                if len(tool_result_str) > 2000:
                    stored_result = tool_result_str[:2000] + f"\n... [truncated, {len(tool_result_str)} total chars]"
                else:
                    stored_result = tool_result_str
                
                function_response_parts.append({
                    'function_response': {
                        'name': tool_name,
                        'response': {'result': stored_result}
                    }
                })
            
            self._add_to_history('user', function_response_parts)
        
        if iteration >= max_iterations:
            console.print("\n[bold yellow](Max iterations reached)[/bold yellow]")
            
    async def _bg_task(self, tool_name: str, tool_arguments: dict):
        """Actually call the given MCP tool in the background and notify the model with the result."""
        print(f"\n⚙️ Background task started: {tool_name}({json.dumps(tool_arguments)})")
        tool_result = await self._call_mcp_tool(tool_name, tool_arguments)
        console.print(f"\n[bold yellow]✅ Background task [cyan]{tool_name}[/cyan] completed![/bold yellow]")
        await self.chat_stream(
            f"The background task '{tool_name}' has finished. Result:\n{tool_result}\nPlease analyze and report back.",
            is_notification=True
        )

    async def _bg_watch(self, resource_type: str, interval: int, watch_args: dict):
        """Poll watch_resource every interval seconds and feed snapshot to the model."""
        while self.active_watches.get(resource_type, False):
            await asyncio.sleep(interval)
            if not self.active_watches.get(resource_type, False):
                break
            # Call the real watch_resource tool to get a fresh snapshot
            try:
                snapshot_raw = await self._call_mcp_tool("watch_resource", watch_args)
                payload = json.loads(snapshot_raw)
                snapshot = payload.get("snapshot", snapshot_raw)
                ts = payload.get("timestamp", "")
            except Exception:
                snapshot = snapshot_raw if isinstance(snapshot_raw, str) else "Error fetching data"
                ts = ""
            
            console.print(f"\n[dim]👁️ Watch tick [{resource_type}] {ts}[/dim]")
            await self.chat_stream(
                f"Watch update for {resource_type} at {ts}:\n{snapshot}\nAnalyze any changes and decide if watching should continue (call stop_watch if done).",
                is_notification=True
            )
    
    async def run_interactive(self):
        console.print("="*60, style="bold cyan")
        console.print("  MCP Client with Google Gemini - TUI MODE", style="bold cyan")
        console.print("="*60, style="bold cyan")
        console.print(f"  Model: [green]{self.model_name}[/green]")
        console.print("  Commands: [yellow]clear[/yellow], [yellow]tools[/yellow], [yellow]exit[/yellow]")
        console.print("="*60, style="bold cyan")
        print()
        
        # Initialize up-arrow history persistence
        history_file = os.path.expanduser('~/.mcp_k8s_history')
        session = PromptSession(history=FileHistory(history_file))
        
        while True:
            try:
                # Use patch_stdout so background tasks can print safely, allow raw ANSI
                with patch_stdout(raw=True):
                    user_input = await session.prompt_async("? You: ")
                
                # Handle Ctrl+C or EOF which returns None
                if user_input is None:
                    console.print("\n[bold yellow]Goodbye![/bold yellow]")
                    break
                    
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit']:
                    console.print("[bold yellow]Goodbye![/bold yellow]")
                    break
                
                if user_input.lower() == 'clear':
                    self.conversation_history = []
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("DELETE FROM history")
                    console.print("[bold green]✓[/bold green] History cleared from database")
                    continue
                
                if user_input.lower() == 'tools':
                    for tool in self.available_tools:
                        console.print(f"  • [cyan]{tool.name}[/cyan]")
                    continue
                
                await self.chat_stream(user_input)
                print()
                
            except KeyboardInterrupt:
                console.print("\n[bold yellow]Goodbye![/bold yellow]")
                break
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
                import traceback
                console.print(traceback.format_exc(), style="red")

async def main():
    client = GeminiMCPClient(
        mcp_server_url="http://localhost:8000/sse",
        model="gemma-4-31b-it",
        api_key=GENI_API_KEY
    )
    
    try:
        await client.connect()
        await client.run_interactive()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
