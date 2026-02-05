"""
Strip sensitive headers from responses
"""

class StripSensitiveHeadersMiddleware:
    """Remove potentially sensitive headers from responses"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Remove sensitive headers
        sensitive_headers = [
            'Server',
            'X-Powered-By',
            'X-AspNet-Version',
            'X-AspNetMvc-Version',
        ]
        
        for header in sensitive_headers:
            if header in response:
                del response[header]
        
        return response
