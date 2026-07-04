"""Grafana MCP Tool Interface"""
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class GrafanaTool:
    """MCP-compliant Grafana operations"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Content-Type': 'application/json'
        }
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Grafana API"""
        try:
            url = f'{self.base_url}{endpoint}'
            response = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            
            if response.ok:
                return {
                    'success': True,
                    'data': response.json() if response.content else None,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'data': None,
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except requests.RequestException as e:
            return {
                'success': False,
                'data': None,
                'error': str(e)
            }
    
    def view_dashboard(self, dashboard_uid: str) -> Dict[str, Any]:
        """Get dashboard by UID"""
        result = self._request('GET', f'/api/dashboards/uid/{dashboard_uid}')
        
        if result['success'] and result['data']:
            dash = result['data'].get('dashboard', {})
            return {
                'success': True,
                'data': {
                    'uid': dash.get('uid'),
                    'title': dash.get('title'),
                    'tags': dash.get('tags', []),
                    'timezone': dash.get('timezone'),
                    'panels': len(dash.get('panels', [])),
                    'version': dash.get('version'),
                    'url': f'{self.base_url}/d/{dashboard_uid}'
                },
                'error': None
            }
        
        return result
    
    def list_dashboards(self, tag: Optional[str] = None) -> Dict[str, Any]:
        """List all dashboards"""
        params = {}
        if tag:
            params['tag'] = tag
        
        result = self._request('GET', '/api/search', params=params)
        
        if result['success']:
            dashboards = []
            for item in result['data'] or []:
                if item.get('type') == 'dash-db':
                    dashboards.append({
                        'uid': item.get('uid'),
                        'title': item.get('title'),
                        'tags': item.get('tags', []),
                        'url': f'{self.base_url}/d/{item.get("uid")}'
                    })
            
            return {
                'success': True,
                'data': dashboards,
                'error': None
            }
        
        return result
    
    def query_metrics(
        self,
        query: str,
        datasource_uid: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute Prometheus/Loki query"""
        if not time_range:
            # Default: last 1 hour
            now = datetime.utcnow()
            time_range = {
                'from': (now - timedelta(hours=1)).isoformat() + 'Z',
                'to': now.isoformat() + 'Z'
            }
        
        payload = {
            'queries': [{
                'refId': 'A',
                'expr': query,
                'datasource': {'uid': datasource_uid} if datasource_uid else None
            }],
            'from': time_range['from'],
            'to': time_range['to']
        }
        
        result = self._request('POST', '/api/ds/query', json=payload)
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'query': query,
                    'time_range': time_range,
                    'results': result['data']
                },
                'error': None
            }
        
        return result
    
    def list_alerts(self) -> Dict[str, Any]:
        """List alert rules"""
        result = self._request('GET', '/api/v1/provisioning/alert-rules')
        
        if result['success']:
            alerts = []
            for alert in result['data'] or []:
                alerts.append({
                    'uid': alert.get('uid'),
                    'title': alert.get('title'),
                    'condition': alert.get('condition'),
                    'folder': alert.get('folderUID'),
                    'no_data_state': alert.get('noDataState'),
                    'exec_err_state': alert.get('execErrState')
                })
            
            return {
                'success': True,
                'data': alerts,
                'error': None
            }
        
        return result
    
    def create_alert(
        self,
        title: str,
        condition: str,
        folder_uid: str,
        datasource_uid: str,
        interval: int = 60
    ) -> Dict[str, Any]:
        """Create alert rule"""
        payload = {
            'title': title,
            'condition': condition,
            'folderUID': folder_uid,
            'ruleGroup': 'default',
            'noDataState': 'NoData',
            'execErrState': 'Alerting',
            'for': f'{interval}s',
            'data': [{
                'refId': 'A',
                'queryType': '',
                'relativeTimeRange': {'from': 600, 'to': 0},
                'datasourceUid': datasource_uid,
                'model': {
                    'expr': condition,
                    'refId': 'A'
                }
            }]
        }
        
        result = self._request('POST', '/api/v1/provisioning/alert-rules', json=payload)
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'title': title,
                    'message': 'Alert created successfully',
                    'uid': result['data'].get('uid')
                },
                'error': None
            }
        
        return result
    
    def delete_alert(self, alert_uid: str) -> Dict[str, Any]:
        """Delete alert rule"""
        result = self._request('DELETE', f'/api/v1/provisioning/alert-rules/{alert_uid}')
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'uid': alert_uid,
                    'message': 'Alert deleted successfully'
                },
                'error': None
            }
        
        return result
    
    def list_datasources(self) -> Dict[str, Any]:
        """List datasources"""
        result = self._request('GET', '/api/datasources')
        
        if result['success']:
            datasources = []
            for ds in result['data'] or []:
                datasources.append({
                    'uid': ds.get('uid'),
                    'name': ds.get('name'),
                    'type': ds.get('type'),
                    'url': ds.get('url'),
                    'is_default': ds.get('isDefault', False)
                })
            
            return {
                'success': True,
                'data': datasources,
                'error': None
            }
        
        return result
    
    def modify_datasource(self, datasource_uid: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Modify datasource configuration"""
        # First get current config
        get_result = self._request('GET', f'/api/datasources/uid/{datasource_uid}')
        
        if not get_result['success']:
            return get_result
        
        current = get_result['data']
        current.update(updates)
        
        result = self._request('PUT', f'/api/datasources/uid/{datasource_uid}', json=current)
        
        if result['success']:
            return {
                'success': True,
                'data': {
                    'uid': datasource_uid,
                    'message': 'Datasource updated successfully',
                    'updates': updates
                },
                'error': None
            }
        
        return result
