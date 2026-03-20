from abc import ABC, abstractmethod
from datetime import datetime


class AbstractLockProvider(ABC):
    """Interface for smart lock providers."""

    @abstractmethod
    def create_access_code(
        self, device_id: str, code: str, name: str,
        starts_at: datetime, ends_at: datetime,
    ) -> dict:
        """Create a time-bound access code. Returns {external_code_id, status}."""
        ...

    @abstractmethod
    def delete_access_code(self, device_id: str, external_code_id: str) -> bool:
        """Delete/revoke an access code. Returns True on success."""
        ...

    @abstractmethod
    def get_lock_status(self, device_id: str) -> dict:
        """Returns {locked: bool, online: bool, battery_level: float|None}."""
        ...

    @abstractmethod
    def lock(self, device_id: str) -> bool:
        ...

    @abstractmethod
    def unlock(self, device_id: str) -> bool:
        ...


class AbstractThermostatProvider(ABC):
    """Interface for thermostat providers."""

    @abstractmethod
    def set_temperature(self, device_id: str, heat_f: float, cool_f: float) -> bool:
        ...

    @abstractmethod
    def set_mode(self, device_id: str, mode: str) -> bool:
        """mode: 'heat', 'cool', 'auto', 'off', 'eco'"""
        ...

    @abstractmethod
    def get_status(self, device_id: str) -> dict:
        """Returns {temperature_f, mode, online, humidity}."""
        ...


class AbstractNoiseSensorProvider(ABC):
    """Interface for noise sensor providers."""

    @abstractmethod
    def get_current_reading(self, device_id: str) -> dict:
        """Returns {decibel_level, online, battery_level}."""
        ...

    @abstractmethod
    def set_noise_threshold(self, device_id: str, threshold_db: float) -> bool:
        ...
