import gradio as gr
import sqlite3
from datetime import datetime
from typing import Optional, Tuple
import json

from core.auth import verify_totp, create_session, validate_session, get_admin_by_session
from core.database import get_db_connection
from agent.graph import agent_graph
from agent.state import AgentState

# Color palette
PRIMARY_BLUE = "#3B82F6"
WHITE = "#FFFFFF"
PURPLE = "#8B5CF6"


def login(username: str, otp: str) -> Tuple[str, str]:
    """Handle admin login with TOTP"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, totp_secret, role FROM admins WHERE username = ?", (username,))
    admin = cursor.fetchone()
    
    if not admin:
        return None, "❌ Invalid username"
    
    admin_id, totp_secret, role = admin
    
    if not verify_totp(totp_secret, otp):
        return None, "❌ Invalid OTP"
    
    session_id = create_session(admin_id)
    conn.close()
    
    return session_id, f"✅ Welcome, {username} ({role})"


def chat_interface(message: str, history: list, session_id: str) -> Tuple[list, str]:
    """Main chat interface for agent interaction"""
    
    if not session_id:
        history.append((message, "❌ Please login first"))
        return history, ""
    
    admin = get_admin_by_session(session_id)
    if not admin:
        history.append((message, "❌ Session expired, please login again"))
        return history, ""
    
    # Initialize state
    state: AgentState = {
        'session_id': session_id,
        'admin_id': admin['id'],
        'username': admin['username'],
        'role': admin['role'],
        'user_input': message,
        'parsed_action': None,
        'is_allowed': False,
        'risk_level': None,
        'requires_approval': False,
        'approval_status': None,
        'supervisor_session': None,
        'execution_result': None,
        'error_message': None,
        'messages': [],
        'next_action': 'parse'
    }
    
    # Run agent graph
    result = agent_graph.invoke(state)
    
    # Extract response
    if result['messages']:
        response = result['messages'][-1]['content']
    else:
        response = "No response generated"
    
    history.append((message, response))
    
    return history, ""


def approval_queue_interface(session_id: str) -> str:
    """Display pending approval requests (supervisor only)"""
    
    if not session_id:
        return "❌ Please login first"
    
    admin = get_admin_by_session(session_id)
    if not admin or admin['role'] != 'supervisor':
        return "❌ Supervisor access required"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, admin_id, action, resource_type, resource_id, risk_level, details, timestamp
        FROM audit_log
        WHERE status = 'pending_approval'
        ORDER BY timestamp DESC
    """)
    
    pending = cursor.fetchall()
    conn.close()
    
    if not pending:
        return "✅ No pending approvals"
    
    output = "## 🔐 Pending Approvals\n\n"
    for row in pending:
        log_id, admin_id, action, resource_type, resource_id, risk_level, details, timestamp = row
        output += f"**ID:** {log_id}\n"
        output += f"**Requested by:** Admin #{admin_id}\n"
        output += f"**Action:** `{action}` on `{resource_type}`\n"
        output += f"**Risk Level:** {risk_level}\n"
        output += f"**Details:**```json\n{details}\n```\n"
        output += f"**Time:** {timestamp}\n"
        output += "---\n\n"
    
    return output


def approve_action(log_id: int, otp: str, session_id: str) -> str:
    """Approve a pending action with supervisor OTP"""
    
    if not session_id:
        return "❌ Please login first"
    
    admin = get_admin_by_session(session_id)
    if not admin or admin['role'] != 'supervisor':
        return "❌ Supervisor access required"
    
    # Verify OTP
    if not verify_totp(admin['totp_secret'], otp):
        return "❌ Invalid OTP"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update approval status
    cursor.execute("""
        UPDATE audit_log
        SET status = 'approved', supervisor_id = ?
        WHERE id = ? AND status = 'pending_approval'
    """, (admin['id'], log_id))
    
    conn.commit()
    
    if cursor.rowcount == 0:
        conn.close()
        return "❌ Approval request not found or already processed"
    
    conn.close()
    return f"✅ Action #{log_id} approved successfully"


def deny_action(log_id: int, reason: str, session_id: str) -> str:
    """Deny a pending action"""
    
    if not session_id:
        return "❌ Please login first"
    
    admin = get_admin_by_session(session_id)
    if not admin or admin['role'] != 'supervisor':
        return "❌ Supervisor access required"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE audit_log
        SET status = 'denied', supervisor_id = ?, details = json_set(details, '$.denial_reason', ?)
        WHERE id = ? AND status = 'pending_approval'
    """, (admin['id'], reason, log_id))
    
    conn.commit()
    
    if cursor.rowcount == 0:
        conn.close()
        return "❌ Approval request not found or already processed"
    
    conn.close()
    return f"✅ Action #{log_id} denied"


def audit_log_viewer(session_id: str, limit: int = 50) -> str:
    """View audit log (supervisor only)"""
    
    if not session_id:
        return "❌ Please login first"
    
    admin = get_admin_by_session(session_id)
    if not admin or admin['role'] != 'supervisor':
        return "❌ Supervisor access required"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, admin_id, action, resource_type, resource_id, status, risk_level, timestamp
        FROM audit_log
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    
    logs = cursor.fetchall()
    conn.close()
    
    if not logs:
        return "No audit logs found"
    
    output = "## 📋 Audit Log\n\n"
    output += "| ID | Admin | Action | Resource | Status | Risk | Time |\n"
    output += "|---|---|---|---|---|---|---|\n"
    
    for row in logs:
        log_id, admin_id, action, resource_type, resource_id, status, risk_level, timestamp = row
        output += f"| {log_id} | {admin_id} | {action} | {resource_type}:{resource_id or 'N/A'} | {status} | {risk_level} | {timestamp} |\n"
    
    return output


# Build Gradio UI
with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue", secondary_hue="purple")) as demo:
    session_state = gr.State(value=None)
    
    gr.Markdown("# 🛡️ DevOps Guardian")
    gr.Markdown("AI-powered DevOps administration with policy enforcement and supervisor approval")
    
    with gr.Tab("🔐 Login"):
        with gr.Row():
            username_input = gr.Textbox(label="Username", placeholder="admin")
            otp_input = gr.Textbox(label="OTP", placeholder="6-digit code", type="password")
        
        login_btn = gr.Button("Login", variant="primary")
        login_output = gr.Textbox(label="Status", interactive=False)
        
        login_btn.click(
            fn=login,
            inputs=[username_input, otp_input],
            outputs=[session_state, login_output]
        )
    
    with gr.Tab("💬 Agent Chat"):
        chatbot = gr.Chatbot(label="DevOps Guardian Agent", height=500)
        msg_input = gr.Textbox(label="Your request", placeholder="Show me pods in production namespace")
        
        msg_input.submit(
            fn=chat_interface,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, msg_input]
        )
    
    with gr.Tab("✅ Approval Queue"):
        gr.Markdown("### Pending High-Risk Actions (Supervisor Only)")
        
        refresh_btn = gr.Button("Refresh Queue")
        queue_output = gr.Markdown()
        
        with gr.Row():
            approve_id = gr.Number(label="Action ID to Approve", precision=0)
            approve_otp = gr.Textbox(label="Supervisor OTP", type="password")
        
        approve_btn = gr.Button("Approve", variant="primary")
        
        with gr.Row():
            deny_id = gr.Number(label="Action ID to Deny", precision=0)
            deny_reason = gr.Textbox(label="Reason")
        
        deny_btn = gr.Button("Deny", variant="stop")
        
        action_output = gr.Textbox(label="Result", interactive=False)
        
        refresh_btn.click(
            fn=approval_queue_interface,
            inputs=[session_state],
            outputs=[queue_output]
        )
        
        approve_btn.click(
            fn=approve_action,
            inputs=[approve_id, approve_otp, session_state],
            outputs=[action_output]
        )
        
        deny_btn.click(
            fn=deny_action,
            inputs=[deny_id, deny_reason, session_state],
            outputs=[action_output]
        )
    
    with gr.Tab("📋 Audit Log"):
        gr.Markdown("### System Audit Trail (Supervisor Only)")
        
        log_limit = gr.Slider(minimum=10, maximum=200, value=50, step=10, label="Number of entries")
        view_log_btn = gr.Button("View Audit Log")
        log_output = gr.Markdown()
        
        view_log_btn.click(
            fn=audit_log_viewer,
            inputs=[session_state, log_limit],
            outputs=[log_output]
        )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
