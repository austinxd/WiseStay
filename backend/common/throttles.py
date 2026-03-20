from rest_framework.throttling import SimpleRateThrottle


class RoleBasedRateThrottle(SimpleRateThrottle):
    scope = "anon"  # Default scope; overridden per-request in get_cache_key

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            self.scope = "anon"
            ident = self.get_ident(request)
        else:
            self.scope = getattr(request.user, "role", "guest")
            ident = request.user.pk
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class WebhookRateThrottle(SimpleRateThrottle):
    scope = "webhook"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
