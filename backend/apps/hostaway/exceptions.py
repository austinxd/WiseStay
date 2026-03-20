class HostawayAPIError(Exception):
    """Error from Hostaway API."""

    def __init__(self, message: str, status_code: int = None, response_body=None, endpoint: str = ""):
        self.status_code = status_code
        self.response_body = response_body
        self.endpoint = endpoint
        super().__init__(message)


class HostawayAuthError(HostawayAPIError):
    """Authentication failure (401/403)."""
    pass


class HostawayRateLimitError(HostawayAPIError):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str, retry_after: int = None, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class HostawaySyncConflictError(Exception):
    """Conflict during sync (e.g. listing exists locally but not in Hostaway)."""
    pass


class HostawayWebhookValidationError(Exception):
    """Invalid webhook payload."""
    pass
