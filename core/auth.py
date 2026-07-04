import pyotp
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from core.database import (
    get_admin_by_username,
    update_last_login,
    create_session,
    get_session,
)

SESSION_DURATION_HOURS = 8


def authenticate(username: str, otp_code: str, ip_address: str = '0.0.0.0') -> Optional[Dict[str, Any]]:
    """
    Authenticate admin with username + OTP.
    
    Returns session dict or None.
    """
    admin = get_admin_by_username(username)
    
    if not admin:
        return None
    
    # Verify OTP
    totp = pyotp.TOTP(admin['otp_secret'])
    if not totp.verify(otp_code, valid_window=1):
        return None
    
    # Create session
    session_id = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(hours=SESSION_DURATION_HOURS)).isoformat()
    
    create_session(session_id, admin['admin_id'], ip_address, expires_at)
    update_last_login(admin['admin_id'])
    
    return {
        'session_id': session_id,
        'admin_id': admin['admin_id'],
        'username': admin['username'],
        'role': admin['role'],
        'expires_at': expires_at,
    }


def verify_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Verify session is valid and active"""
    return get_session(session_id)
