from typing import TypedDict, Optional, List, Dict, Any, Literal

class AgentState(TypedDict):
    """State for DevOps Guardian agent"""
    # Session context
    session_id: Optional[str]
    admin_id: Optional[int]
    username: Optional[str]
    role: Optional[str]
    
    # Current request
    user_input: str
    parsed_action: Optional[Dict[str, Any]]  # {resource_type, action, params}
    
    # Permission check results
    is_allowed: bool
    risk_level: Optional[str]
    requires_approval: bool
    approval_status: Optional[Literal['pending', 'approved', 'denied']]
    supervisor_session: Optional[str]
    
    # Execution results
    execution_result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    
    # Conversation history
    messages: List[Dict[str, str]]
    
    # Next step
    next_action: Literal['parse', 'check_permission', 'request_approval', 'execute', 'respond', 'end']
