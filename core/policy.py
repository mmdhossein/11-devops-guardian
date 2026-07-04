import yaml
from typing import Dict, Any, Tuple

class PolicyEngine:
    def __init__(self, policy_path: str = 'config/permissions.yaml'):
        with open(policy_path, 'r') as f:
            self.policy = yaml.safe_load(f)
    
    def check_permission(self, role: str, resource_type: str, action: str) -> Tuple[bool, str, bool]:
        """
        Check if role can perform action on resource_type.
        
        Returns:
            (allowed, risk_level, requires_approval)
        """
        if resource_type not in self.policy['permissions']:
            return False, 'unknown', False
        
        resource_perms = self.policy['permissions'][resource_type]
        
        if action not in resource_perms:
            return False, 'unknown', False
        
        action_policy = resource_perms[action]
        
        allowed = role in action_policy['allowed_roles']
        risk_level = action_policy['risk_level']
        requires_approval = action_policy['requires_approval']
        
        return allowed, risk_level, requires_approval
    
    def can_approve(self, role: str) -> bool:
        """Check if role can approve requests"""
        return self.policy['roles'].get(role, {}).get('can_approve', False)
