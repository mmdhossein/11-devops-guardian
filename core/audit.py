from core.database import get_db
from typing import Optional

def log_action(
    admin_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    status: str,
    risk_level: str,
    details: Optional[str] = None
):
    """Write audit log entry"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_log (admin_id, action, resource_type, resource_id, status, risk_level, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (admin_id, action, resource_type, resource_id, status, risk_level, details))
        conn.commit()


def get_recent_logs(limit: int = 50):
    """Fetch recent audit logs"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                l.log_id,
                a.username,
                l.action,
                l.resource_type,
                l.resource_id,
                l.status,
                l.risk_level,
                l.details,
                l.timestamp
            FROM audit_log l
            JOIN admins a ON l.admin_id = a.admin_id
            ORDER BY l.timestamp DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
