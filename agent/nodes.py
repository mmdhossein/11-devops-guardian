import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from agent.state import AgentState
from core.policy import PolicyEngine
from core.audit import log_action
from tools.kubernetes import KubernetesTool
from tools.argocd import ArgoCDTool
from tools.grafana import GrafanaTool

# Initialize tools
k8s_tool = KubernetesTool()
argocd_tool = ArgoCDTool()
grafana_tool = GrafanaTool(base_url='http://localhost:3000')  # Configure as needed

# Initialize policy engine
policy_engine = PolicyEngine()

# Initialize LLM
llm = ChatOpenAI(model='gpt-4', temperature=0)


def parse_intent_node(state: AgentState) -> AgentState:
    """Parse user input to extract action intent"""
    
    system_prompt = """You are a DevOps intent parser. Extract structured action from user request.

Available resources:
- kubernetes: get_pods, get_logs, restart_pod, delete_pod, scale_deployment, delete_deployment, get_deployments
- argocd: list_applications, get_application, sync_application, rollback_application, delete_application
- grafana: view_dashboard, list_dashboards, query_metrics, list_alerts, create_alert, delete_alert, list_datasources, modify_datasource

Return JSON with:
{
  "resource_type": "kubernetes|argocd|grafana",
  "action": "action_name",
  "params": {...}
}

If unclear, return {"resource_type": "unknown", "action": "clarify", "params": {"message": "..."}}
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User request: {state['user_input']}")
    ]
    
    response = llm.invoke(messages)
    
    try:
        parsed = json.loads(response.content)
        state['parsed_action'] = parsed
        state['next_action'] = 'check_permission' if parsed['resource_type'] != 'unknown' else 'respond'
    except json.JSONDecodeError:
        state['error_message'] = 'Failed to parse intent'
        state['next_action'] = 'respond'
    
    return state


def check_permission_node(state: AgentState) -> AgentState:
    """Check if user has permission for action"""
    
    parsed = state['parsed_action']
    role = state['role']
    
    allowed, risk_level, requires_approval = policy_engine.check_permission(
        role=role,
        resource_type=parsed['resource_type'],
        action=parsed['action']
    )
    
    state['is_allowed'] = allowed
    state['risk_level'] = risk_level
    state['requires_approval'] = requires_approval
    
    if not allowed:
        state['error_message'] = f"Permission denied: {role} cannot perform {parsed['action']} on {parsed['resource_type']}"
        state['next_action'] = 'respond'
    elif requires_approval:
        state['approval_status'] = 'pending'
        state['next_action'] = 'request_approval'
    else:
        state['next_action'] = 'execute'
    
    return state


def request_approval_node(state: AgentState) -> AgentState:
    """Request supervisor approval (human-in-the-loop)"""
    
    # This node returns control to UI for approval workflow
    # UI will update state with approval_status and supervisor_session
    
    parsed = state['parsed_action']
    state['messages'].append({
        'role': 'assistant',
        'content': f"⚠️ **Approval Required**\n\n"
                   f"Action: `{parsed['action']}` on `{parsed['resource_type']}`\n"
                   f"Risk Level: **{state['risk_level']}**\n"
                   f"Parameters: `{json.dumps(parsed['params'], indent=2)}`\n\n"
                   f"Supervisor approval needed to proceed."
    })
    
    state['next_action'] = 'execute'  # Will execute after approval
    return state


def execute_action_node(state: AgentState) -> AgentState:
    """Execute the requested action"""
    
    parsed = state['parsed_action']
    resource_type = parsed['resource_type']
    action = parsed['action']
    params = parsed['params']
    
    result = None
    
    try:
        # Route to appropriate tool
        if resource_type == 'kubernetes':
            result = _execute_k8s_action(action, params)
        elif resource_type == 'argocd':
            result = _execute_argocd_action(action, params)
        elif resource_type == 'grafana':
            result = _execute_grafana_action(action, params)
        else:
            result = {'success': False, 'error': 'Unknown resource type'}
        
        state['execution_result'] = result
        
        # Log to audit
        log_action(
            admin_id=state['admin_id'],
            action=action,
            resource_type=resource_type,
            resource_id=params.get('name') or params.get('app_name') or params.get('dashboard_uid'),
            status='success' if result.get('success') else 'failure',
            risk_level=state['risk_level'],
            details=json.dumps(params)
        )
        
    except Exception as e:
        state['error_message'] = str(e)
        log_action(
            admin_id=state['admin_id'],
            action=action,
            resource_type=resource_type,
            resource_id=None,
            status='error',
            risk_level=state['risk_level'],
            details=str(e)
        )
    
    state['next_action'] = 'respond'
    return state

def _execute_k8s_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Kubernetes action"""
    if action == 'get_pods':
        return k8s_tool.get_pods(params.get('namespace', 'default'))
    elif action == 'get_logs':
        return k8s_tool.get_logs(params['pod_name'], params.get('namespace', 'default'), params.get('tail', 100))
    elif action == 'restart_pod':
        return k8s_tool.restart_pod(params['pod_name'], params.get('namespace', 'default'))
    elif action == 'delete_pod':
        return k8s_tool.delete_pod(params['pod_name'], params.get('namespace', 'default'))
    elif action == 'scale_deployment':
        return k8s_tool.scale_deployment(params['deployment_name'], params['replicas'], params.get('namespace', 'default'))
    elif action == 'delete_deployment':
        return k8s_tool.delete_deployment(params['deployment_name'], params.get('namespace', 'default'))
    elif action == 'get_deployments':
        return k8s_tool.get_deployments(params.get('namespace', 'default'))
    else:
        return {'success': False, 'error': f'Unknown Kubernetes action: {action}'}


def _execute_argocd_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute ArgoCD action"""
    if action == 'list_applications':
        return argocd_tool.list_applications()
    elif action == 'get_application':
        return argocd_tool.get_application(params['app_name'])
    elif action == 'sync_application':
        return argocd_tool.sync_application(
            params['app_name'],
            params.get('prune', False),
            params.get('force', False)
        )
    elif action == 'rollback_application':
        return argocd_tool.rollback_application(params['app_name'], params.get('revision'))
    elif action == 'delete_application':
        return argocd_tool.delete_application(params['app_name'], params.get('cascade', True))
    elif action == 'get_sync_history':
        return argocd_tool.get_sync_history(params['app_name'], params.get('limit', 10))
    else:
        return {'success': False, 'error': f'Unknown ArgoCD action: {action}'}


def _execute_grafana_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Grafana action"""
    if action == 'view_dashboard':
        return grafana_tool.view_dashboard(params['dashboard_uid'])
    elif action == 'list_dashboards':
        return grafana_tool.list_dashboards(params.get('tag'))
    elif action == 'query_metrics':
        return grafana_tool.query_metrics(
            params['query'],
            params.get('datasource_uid'),
            params.get('time_range')
        )
    elif action == 'list_alerts':
        return grafana_tool.list_alerts()
    elif action == 'create_alert':
        return grafana_tool.create_alert(
            params['title'],
            params['condition'],
            params['folder_uid'],
            params['datasource_uid'],
            params.get('interval', 60)
        )
    elif action == 'delete_alert':
        return grafana_tool.delete_alert(params['alert_uid'])
    elif action == 'list_datasources':
        return grafana_tool.list_datasources()
    elif action == 'modify_datasource':
        return grafana_tool.modify_datasource(params['datasource_uid'], params['updates'])
    else:
        return {'success': False, 'error': f'Unknown Grafana action: {action}'}


def respond_node(state: AgentState) -> AgentState:
    """Format final response to user"""
    
    if state.get('error_message'):
        state['messages'].append({
            'role': 'assistant',
            'content': f"❌ **Error:** {state['error_message']}"
        })
    elif state.get('execution_result'):
        result = state['execution_result']
        if result.get('success'):
            content = f"✅ **Success**\n\n```json\n{json.dumps(result.get('data'), indent=2)}\n```"
        else:
            content = f"❌ **Failed:** {result.get('error')}"
        
        state['messages'].append({
            'role': 'assistant',
            'content': content
        })
    
    state['next_action'] = 'end'
    return state
