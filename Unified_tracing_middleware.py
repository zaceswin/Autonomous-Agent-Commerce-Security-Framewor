import json
import re
import requests
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Initialize the tracer for this module
tracer = trace.get_tracer("agent.security.guardrails")
OPA_URL = "http://localhost:8181/v1/data/agent_policy/allow"

def contains_malicious_payload(args: dict) -> bool:
    """Semantic filter to catch prompt injections or unauthorized DB commands."""
    payload_str = json.dumps(args).lower()
    # Basic rule-based filtering (in production, use Lakera Guard or similar API)
    suspicious_patterns = [
        r"drop table", r"ignore previous instructions", r"system\(", r"exec\("
    ]
    return any(re.search(p, payload_str) for p in suspicious_patterns)

def check_opa_policy(agent_role: str, tool_name: str, method: str) -> bool:
    """Queries the OPA server to verify RBAC permissions."""
    input_data = {"input": {"role": agent_role, "tool": tool_name, "method": method}}
    try:
        response = requests.post(OPA_URL, json=input_data, timeout=2.0)
        return response.json().get("result", False)
    except requests.exceptions.RequestException:
        # Fail secure: block the action if the policy engine is unreachable
        return False

def tool_execution_wrapper(tool_name: str, method: str, args: dict, agent_role: str):
    """The main interceptor that wraps the agent's tool execution."""
    with tracer.start_as_current_span(f"AgentTool.{tool_name}") as span:
        # Attach base metadata to the trace
        span.set_attribute("agent.role", agent_role)
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.method", method)
        
        # 1. Evaluate OPA Policy
        if not check_opa_policy(agent_role, tool_name, method):
            span.set_attribute("security.guardrail.blocked", True)
            span.set_attribute("security.block_reason", "opa_policy_violation")
            span.set_status(Status(StatusCode.ERROR, "Blocked by OPA RBAC"))
            return f"SYSTEM_ERROR: Unauthorized tool '{tool_name}'."
        
        # 2. Evaluate Semantic Filter
        if contains_malicious_payload(args):
            span.set_attribute("security.guardrail.blocked", True)
            span.set_attribute("security.block_reason", "semantic_payload_violation")
            span.set_status(Status(StatusCode.ERROR, "Blocked by semantic filter"))
            return "SYSTEM_ERROR: Payload rejected due to security policy."
        
        # 3. Execution Phase
        try:
            span.set_attribute("security.guardrail.blocked", False)
            # result = execute_actual_tool(tool_name, args)
            result = f"Successfully executed {tool_name}" # Mocked execution
            span.set_status(Status(StatusCode.OK))
            return result
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            return f"SYSTEM_ERROR: Execution failed - {str(e)}"
