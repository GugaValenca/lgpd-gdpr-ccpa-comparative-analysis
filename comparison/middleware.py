"""
A minimal Content-Security-Policy middleware.

Django 6.0 ships CSP support built in (`django.middleware.csp`); this
project pins Django 5.2 (the LTS release current when it was built), which
doesn't have it yet, so this is a small stand-in with the same strict
policy: same-origin only, no inline/eval script, no plugins, no framing.
`data:` is allowed for images only because the Django admin's own static
CSS embeds its icons as data: URIs.
"""

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


class ContentSecurityPolicyMiddleware:
    """Adds a strict Content-Security-Policy header to every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        return response
