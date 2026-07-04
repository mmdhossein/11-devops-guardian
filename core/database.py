import sqlite3
from contextlib import contextmanager
from typing import Optional, Dict, Any

DB_PATH = 'devops_guardian.db'

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_admin_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Fetch admin by username"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT admin_id, username, role, otp_secret, email, is_active, last_login
            FROM admins
            WHERE username = ? AND is_active = 1
        ''', (username,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_last_login(admin_id: int):
    """Update admin's last login timestamp"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE admins
            SET last_login = CURRENT_TIMESTAMP
            WHERE admin_id = ?
        ''', (admin_id,))
        conn.commit()


def create_session(session_id: str, admin_id: int, ip_address: str, expires_at: str):
    """Create new session"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO admin_sessions (session_id, admin_id, ip_address, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (session_id, admin_id, ip_address, expires_at))
        conn.commit()


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Fetch active session"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, a.username, a.role
            FROM admin_sessions s
            JOIN admins a ON s.admin_id = a.admin_id
            WHERE s.session_id = ? AND s.expires_at > CURRENT_TIMESTAMP
        ''', (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def cleanup_expired_sessions():
    """Remove expired sessions"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM admin_sessions WHERE expires_at <= CURRENT_TIMESTAMP')
        conn.commit()
