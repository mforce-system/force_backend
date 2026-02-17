"""
Health check view for Docker healthchecks and monitoring
"""
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db import connection
from django.core.cache import cache
import json


class HealthCheckView(APIView):
    """Health check endpoint for containers and monitoring"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return health status"""
        health_status = {
            'status': 'healthy',
            'checks': {}
        }
        
        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            health_status['checks']['database'] = 'ok'
        except Exception as e:
            health_status['checks']['database'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Cache (Redis) check
        try:
            cache.set('health_check', 'ok', 10)
            cache.get('health_check')
            health_status['checks']['cache'] = 'ok'
        except Exception as e:
            health_status['checks']['cache'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
        
        return Response(health_status)
