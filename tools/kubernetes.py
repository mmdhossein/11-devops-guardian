"""Kubernetes MCP Tool Interface"""
import subprocess
import json
from typing import Dict, Any, List, Optional

class KubernetesTool:
    """MCP-compliant Kubernetes operations"""
    
    def __init__(self, kubeconfig: Optional[str] = None):
        self.kubeconfig = kubeconfig
        self.base_cmd = ['kubectl']
        if kubeconfig:
            self.base_cmd.extend(['--kubeconfig', kubeconfig])
    
    def _run_kubectl(self, args: List[str]) -> Dict[str, Any]:
        """Execute kubectl command and return structured result"""
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
    
    def get_pods(self, namespace: str = 'default') -> Dict[str, Any]:
        """List pods in namespace"""
        result = self._run_kubectl(['get', 'pods', '-n', namespace, '-o', 'json'])
        
        if result['success']:
            try:
                pods_data = json.loads(result['output'])
                pods = []
                for item in pods_data.get('items', []):
                    pods.append({
                        'name': item['metadata']['name'],
                        'namespace': item['metadata']['namespace'],
                        'status': item['status']['phase'],
                        'ready': self._get_ready_status(item),
                        'restarts': self._get_restart_count(item),
                        'age': item['metadata']['creationTimestamp']
                    })
                
                return {
                    'success': True,
                    'data': pods,
                    'error': None
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'data': None,
                    'error': 'Failed to parse kubectl output'
                }
        
        return result
    
    def get_logs(self, pod_name: str, namespace: str = 'default', tail: int = 100) -> Dict[str, Any]:
        """Get pod logs"""
        result = self._run_kubectl([
            'logs',
            pod_name,
            '-n', namespace,
            '--tail', str(tail)
        ])
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'pod': pod_name,
                    'namespace': namespace,
                    'logs': result['output']
                },
                'error': None
            }
        
        return result
    
    def restart_pod(self, pod_name: str, namespace: str = 'default') -> Dict[str, Any]:
        """Restart pod by deleting it (will be recreated by controller)"""
        result = self._run_kubectl(['delete', 'pod', pod_name, '-n', namespace])
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'pod': pod_name,
                    'namespace': namespace,
                    'action': 'restart',
                    'message': 'Pod deleted, controller will recreate it'
                },
                'error': None
            }
        
        return result
    
    def delete_pod(self, pod_name: str, namespace: str = 'default') -> Dict[str, Any]:
        """Delete pod"""
        result = self._run_kubectl(['delete', 'pod', pod_name, '-n', namespace, '--grace-period=30'])
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'pod': pod_name,
                    'namespace': namespace,
                    'action': 'delete',
                    'message': 'Pod deleted successfully'
                },
                'error': None
            }
        
        return result
    
    def scale_deployment(self, deployment_name: str, replicas: int, namespace: str = 'default') -> Dict[str, Any]:
        """Scale deployment"""
        result = self._run_kubectl([
            'scale',
            f'deployment/{deployment_name}',
            f'--replicas={replicas}',
            '-n', namespace
        ])
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'deployment': deployment_name,
                    'namespace': namespace,
                    'replicas': replicas,
                    'message': f'Deployment scaled to {replicas} replicas'
                },
                'error': None
            }
        
        return result
    
    def delete_deployment(self, deployment_name: str, namespace: str = 'default') -> Dict[str, Any]:
        """Delete deployment"""
        result = self._run_kubectl(['delete', 'deployment', deployment_name, '-n', namespace])
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'deployment': deployment_name,
                    'namespace': namespace,
                    'action': 'delete',
                    'message': 'Deployment deleted successfully'
                },
                'error': None
            }
        
        return result
    
    def get_deployments(self, namespace: str = 'default') -> Dict[str, Any]:
        """List deployments"""
        result = self._run_kubectl(['get', 'deployments', '-n', namespace, '-o', 'json'])
        
        if result['success']:
            try:
                data = json.loads(result['output'])
                deployments = []
                for item in data.get('items', []):
                    deployments.append({
                        'name': item['metadata']['name'],
                        'namespace': item['metadata']['namespace'],
                        'replicas': item['spec']['replicas'],
                        'ready': item['status'].get('readyReplicas', 0),
                        'updated': item['status'].get('updatedReplicas', 0),
                        'available': item['status'].get('availableReplicas', 0)
                    })
                
                return {
                    'success': True,
                    'data': deployments,
                    'error': None
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'data': None,
                    'error': 'Failed to parse kubectl output'
                }
        
        return result
    
    def _get_ready_status(self, pod_item: Dict) -> str:
        """Extract ready status from pod spec"""
        container_statuses = pod_item.get('status', {}).get('containerStatuses', [])
        if not container_statuses:
            return '0/0'
        
        ready_count = sum(1 for cs in container_statuses if cs.get('ready', False))
        total_count = len(container_statuses)
        return f'{ready_count}/{total_count}'
    
    def _get_restart_count(self, pod_item: Dict) -> int:
        """Extract total restart count from pod spec"""
        container_statuses = pod_item.get('status', {}).get('containerStatuses', [])
        return sum(cs.get('restartCount', 0) for cs in container_statuses)
