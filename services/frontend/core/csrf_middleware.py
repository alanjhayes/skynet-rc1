from django.middleware.csrf import CsrfViewMiddleware
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


class APICSRFExemptMiddleware:
    """
    Middleware to exempt specific API endpoints from CSRF protection
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # List of URL patterns to exempt from CSRF
        self.exempt_urls = [
            '/api/auth/login/',
            '/api/auth/logout/',
            '/api/auth/refresh/',
        ]

    def __call__(self, request):
        # Check if the request path should be exempt from CSRF
        if any(request.path.startswith(url) for url in self.exempt_urls):
            # Mark the view as CSRF exempt
            request._dont_enforce_csrf_checks = True
        
        response = self.get_response(request)
        return response