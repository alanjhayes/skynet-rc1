import ipaddress
from django.core.exceptions import DisallowedHost
from django.http import HttpResponseBadRequest


class CustomAllowedHostsMiddleware:
    """
    Custom middleware to validate allowed hosts including IP ranges
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        
        if not self.validate_host(host):
            return HttpResponseBadRequest(f"DisallowedHost: {host}")
        
        response = self.get_response(request)
        return response

    def validate_host(self, host):
        # Remove port if present
        if ':' in host:
            host = host.split(':')[0]
        
        # Allow specific hostnames
        allowed_hosts = [
            'localhost', 
            '127.0.0.1', 
            '0.0.0.0', 
            'frontend', 
            'skynet-rc1-frontend', 
            'nginx'
        ]
        
        if host in allowed_hosts:
            return True
        
        # Allow 172.16.0.0/12 range (172.16.0.0 - 172.31.255.255)
        try:
            ip = ipaddress.ip_address(host)
            private_range = ipaddress.ip_network('172.16.0.0/12')
            if ip in private_range:
                return True
        except ValueError:
            pass
        
        return False