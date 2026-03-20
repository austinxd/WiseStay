class DomoticsError(Exception):
    """Base exception for domotics module."""
    pass


class DomoticsProviderError(DomoticsError):
    """Error communicating with device provider (Seam)."""

    def __init__(self, message: str, device_id: str = "", provider: str = "seam"):
        self.device_id = device_id
        self.provider = provider
        super().__init__(message)


class DeviceOfflineError(DomoticsError):
    """Device is not connected/online."""

    def __init__(self, device_id: str, device_name: str = ""):
        self.device_id = device_id
        super().__init__(f"Device '{device_name or device_id}' is offline")


class AccessCodeError(DomoticsError):
    """Error creating or revoking an access code."""
    pass


class DeviceNotFoundError(DomoticsError):
    """Device not found in the property."""
    pass
