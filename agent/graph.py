from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import (
    parse_intent_node,
    check_permission_node,
    request_approval_node,
    execute_action_node,
    respond_node
)


def create_agent_graph():
    """Build LangGraph workflow for DevOps Guardian"""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("check_permission", check_permission_node)
    workflow.add_node("request_approval", request_approval_node)
    workflow.add_node("execute_action", execute_action_node)
    workflow.add_node("respond", respond_node)
    
    # Define edges
    workflow.set_entry_point("parse_intent")
    
    workflow.add_conditional_edges(
        "parse_intent",
        lambda state: state['next_action'],
        {
            "check_permission": "check_permission",
            "respond": "respond"
        }
    )
    
    workflow.add_conditional_edges(
        "check_permission",
        lambda state: state['next_action'],
        {
            "request_approval": "request_approval",
            "execute": "execute_action",
            "respond": "respond"
        }
    )
    
    workflow.add_conditional_edges(
        "request_approval",
        lambda state: state['approval_status'],
        {
            "approved": "execute_action",
            "denied": "respond",
            "pending": END  # Return to UI for approval
        }
    )
    
    workflow.add_edge("execute_action", "respond")
    workflow.add_edge("respond", END)
    
    return workflow.compile()


# Global instance
agent_graph = create_agent_graph()
