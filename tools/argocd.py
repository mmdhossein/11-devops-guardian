"""ArgoCD MCP Tool Interface"""
import subprocess
import json
from typing import Dict, Any, List, Optional

class ArgoCDTool:
    """MCP-compliant ArgoCD operations"""
    
    def __init__(self, server: Optional[str] = None, auth_token: Optional[str] = None):
        self.server = server
        self.auth_token = auth_token
        self.base_cmd = ['argocd']
        
        if server:
            self.base_cmd.extend(['--server', server])
        if auth_token:
            self.base_cmd.extend(['--auth-token', auth_token])
    
    def _run_argocd(self, args: List[str]) -> Dict[str, Any]:
        """Execute argocd CLI command"""
        try:
            result = subprocess.run(
                self.base_cmd + args,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'output': result.stdout,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'output': None,
                    'error': result.stderr
                }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': None,
                'error': 'Command timed out'
            }
        except Exception as e:
            return {
                'success': False,
                'output': None,
                'error': str(e)
            }
    
    def list_applications(self) -> Dict[str, Any]:
        """List all ArgoCD applications"""
        result = self._run_argocd(['app', 'list', '-o', 'json'])
        
        if result['success']:
            try:
                apps_data = json.loads(result['output'])
                apps = []
                
                for app in apps_data if isinstance(apps_data, list) else []:
                    apps.append({
                        'name': app.get('metadata', {}).get('name'),
                        'project': app.get('spec', {}).get('project'),
                        'namespace': app.get('spec', {}).get('destination', {}).get('namespace'),
                        'server': app.get('spec', {}).get('destination', {}).get('server'),
                        'sync_status': app.get('status', {}).get('sync', {}).get('status'),
                        'health_status': app.get('status', {}).get('health', {}).get('status'),
                        'repo': app.get('spec', {}).get('source', {}).get('repoURL')
                    })
                
                return {
                    'success': True,
                    'data': apps,
                    'error': None
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'data': None,
                    'error': 'Failed to parse argocd output'
                }
        
        return result
    
    def get_application(self, app_name: str) -> Dict[str, Any]:
        """Get application details"""
        result = self._run_argocd(['app', 'get', app_name, '-o', 'json'])
        
        if result['success']:
            try:
                app_data = json.loads(result['output'])
                
                return {
                    'success': True,
                    'data': {
                        'name': app_data.get('metadata', {}).get('name'),
                        'project': app_data.get('spec', {}).get('project'),
                        'sync_status': app_data.get('status', {}).get('sync', {}).get('status'),
                        'health_status': app_data.get('status', {}).get('health', {}).get('status'),
                        'revision': app_data.get('status', {}).get('sync', {}).get('revision'),
                        'last_sync': app_data.get('status', {}).get('operationState', {}).get('finishedAt'),
                        'repo': app_data.get('spec', {}).get('source', {}).get('repoURL'),
                        'path': app_data.get('spec', {}).get('source', {}).get('path'),
                        'destination': app_data.get('spec', {}).get('destination')
                    },
                    'error': None
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'data': None,
                    'error': 'Failed to parse application data'
                }
        
        return result
    
    def sync_application(self, app_name: str, prune: bool = False, force: bool = False) -> Dict[str, Any]:
        """Sync application"""
        args = ['app', 'sync', app_name]
        if prune:
            args.append('--prune')
        if force:
            args.append('--force')
        
        result = self._run_argocd(args)
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'application': app_name,
                    'action': 'sync',
                    'prune': prune,
                    'force': force,
                    'message': 'Application sync initiated'
                },
                'error': None
            }
        
        return result
    
    def rollback_application(self, app_name: str, revision: Optional[str] = None) -> Dict[str, Any]:
        """Rollback application to previous or specific revision"""
        args = ['app', 'rollback', app_name]
        if revision:
            args.append(revision)
        
        result = self._run_argocd(args)
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'application': app_name,
                    'action': 'rollback',
                    'revision': revision or 'previous',
                    'message': f'Application rolled back to {revision or "previous revision"}'
                },
                'error': None
            }
        
        return result
    
    def delete_application(self, app_name: str, cascade: bool = True) -> Dict[str, Any]:
        """Delete application"""
        args = ['app', 'delete', app_name, '--yes']
        if cascade:
            args.append('--cascade')
        
        result = self._run_argocd(args)
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'application': app_name,
                    'action': 'delete',
                    'cascade': cascade,
                    'message': 'Application deleted successfully'
                },
                'error': None
            }
        
        return result
    
    def get_sync_history(self, app_name: str, limit: int = 10) -> Dict[str, Any]:
        """Get application sync history"""
        result = self._run_argocd(['app', 'history', app_name, '-o', 'json'])
        
        if result['success']:
            try:
                history_data = json.loads(result['output'])
                history = history_data[:limit] if isinstance(history_data, list) else []
                
                return {
                    'success': True,
                    'data': {
                        'application': app_name,
                        'history': history
                    },
                    'error': None
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'data': None,
                    'error': 'Failed to parse history data'
                }
        
        return result
