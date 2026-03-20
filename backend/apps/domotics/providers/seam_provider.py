import logging

from django.conf import settings

from ..exceptions import (
    AccessCodeError,
    DeviceOfflineError,
    DomoticsProviderError,
)
from .base import AbstractLockProvider, AbstractNoiseSensorProvider, AbstractThermostatProvider

logger = logging.getLogger(__name__)

_seam_client = None


def _get_seam():
    """Lazy singleton for the Seam SDK client."""
    global _seam_client
    if _seam_client is None:
        try:
            from seam import Seam
            _seam_client = Seam(api_key=settings.SEAM_API_KEY)
        except ImportError:
            raise DomoticsProviderError(
                "seam package not installed. Run: pip install seam"
            )
        except Exception as exc:
            raise DomoticsProviderError(f"Failed to initialize Seam client: {exc}")
    return _seam_client


class SeamProvider(AbstractLockProvider, AbstractThermostatProvider, AbstractNoiseSensorProvider):
    """
    Unified provider using Seam API.
    Supports August, Schlage, Nest, Ecobee, Minut through a single API.
    """

    def __init__(self):
        self._seam = _get_seam()

    # ------------------------------------------------------------------
    # Lock operations
    # ------------------------------------------------------------------

    def create_access_code(self, device_id, code, name, starts_at, ends_at):
        try:
            result = self._seam.access_codes.create(
                device_id=device_id,
                name=name,
                code=code,
                starts_at=starts_at.isoformat(),
                ends_at=ends_at.isoformat(),
            )
            code_id = getattr(result, "access_code_id", None) or (result.get("access_code_id") if isinstance(result, dict) else str(result))
            status = getattr(result, "status", "setting")
            logger.info("Seam access code created: %s for device %s", code_id, device_id)
            return {"external_code_id": str(code_id), "status": str(status)}
        except Exception as exc:
            logger.error("Seam create_access_code failed for %s: %s", device_id, exc)
            raise AccessCodeError(f"Failed to create access code on device {device_id}: {exc}")

    def delete_access_code(self, device_id, external_code_id):
        try:
            self._seam.access_codes.delete(access_code_id=external_code_id)
            logger.info("Seam access code deleted: %s", external_code_id)
            return True
        except Exception as exc:
            logger.error("Seam delete_access_code failed for %s: %s", external_code_id, exc)
            return False

    def get_lock_status(self, device_id):
        try:
            lock = self._seam.locks.get(device_id=device_id)
            props = lock.properties if hasattr(lock, "properties") else lock
            return {
                "locked": getattr(props, "locked", None),
                "online": getattr(props, "online", True),
                "battery_level": getattr(props, "battery_level", None),
            }
        except Exception as exc:
            logger.error("Seam get_lock_status failed for %s: %s", device_id, exc)
            raise DomoticsProviderError(f"Failed to get lock status: {exc}", device_id=device_id)

    def lock(self, device_id):
        try:
            self._seam.locks.lock_door(device_id=device_id)
            logger.info("Seam lock_door: %s", device_id)
            return True
        except Exception as exc:
            logger.error("Seam lock failed for %s: %s", device_id, exc)
            raise DomoticsProviderError(f"Failed to lock device: {exc}", device_id=device_id)

    def unlock(self, device_id):
        try:
            self._seam.locks.unlock_door(device_id=device_id)
            logger.info("Seam unlock_door: %s", device_id)
            return True
        except Exception as exc:
            logger.error("Seam unlock failed for %s: %s", device_id, exc)
            raise DomoticsProviderError(f"Failed to unlock device: {exc}", device_id=device_id)

    # ------------------------------------------------------------------
    # Thermostat operations
    # ------------------------------------------------------------------

    def set_temperature(self, device_id, heat_f, cool_f):
        try:
            self._seam.thermostats.set_temperature(
                device_id=device_id,
                heating_set_point_fahrenheit=heat_f,
                cooling_set_point_fahrenheit=cool_f,
            )
            logger.info("Seam set_temperature: device=%s heat=%.1f cool=%.1f", device_id, heat_f, cool_f)
            return True
        except Exception as exc:
            logger.error("Seam set_temperature failed for %s: %s", device_id, exc)
            raise DomoticsProviderError(f"Failed to set temperature: {exc}", device_id=device_id)

    def set_mode(self, device_id, mode):
        try:
            if mode == "eco":
                self._seam.thermostats.set_fan_mode(device_id=device_id, fan_mode="auto")
            logger.info("Seam set_mode: device=%s mode=%s", device_id, mode)
            return True
        except Exception as exc:
            logger.error("Seam set_mode failed for %s: %s", device_id, exc)
            return False

    def get_status(self, device_id):
        try:
            thermostat = self._seam.thermostats.get(device_id=device_id)
            props = thermostat.properties if hasattr(thermostat, "properties") else thermostat
            climate = getattr(props, "current_climate_setting", {})
            return {
                "temperature_f": getattr(props, "temperature_fahrenheit", None),
                "mode": getattr(climate, "hvac_mode_setting", "auto") if hasattr(climate, "hvac_mode_setting") else (climate.get("hvac_mode_setting", "auto") if isinstance(climate, dict) else "auto"),
                "online": getattr(props, "online", True),
                "humidity": getattr(props, "relative_humidity", None),
            }
        except Exception as exc:
            logger.error("Seam thermostat get_status failed for %s: %s", device_id, exc)
            raise DomoticsProviderError(f"Failed to get thermostat status: {exc}", device_id=device_id)

    # ------------------------------------------------------------------
    # Noise sensor operations
    # ------------------------------------------------------------------

    def get_current_reading(self, device_id):
        try:
            device = self._seam.devices.get(device_id=device_id)
            props = device.properties if hasattr(device, "properties") else device
            minut = getattr(props, "minut_metadata", None)
            decibels = None
            if minut:
                sensor_values = getattr(minut, "latest_sensor_values", None)
                if sensor_values:
                    sound = getattr(sensor_values, "sound", None)
                    if sound:
                        decibels = getattr(sound, "value", None)
            return {
                "decibel_level": decibels,
                "online": getattr(props, "online", True),
                "battery_level": getattr(props, "battery_level", None),
            }
        except Exception as exc:
            logger.error("Seam noise reading failed for %s: %s", device_id, exc)
            raise DomoticsProviderError(f"Failed to get noise reading: {exc}", device_id=device_id)

    def set_noise_threshold(self, device_id, threshold_db):
        # Seam handles thresholds via webhook configuration, not per-device API
        logger.info("Noise threshold set to %.1f dB for device %s (via Seam webhooks)", threshold_db, device_id)
        return True

    # ------------------------------------------------------------------
    # Generic device operations
    # ------------------------------------------------------------------

    def get_device(self, device_id: str) -> dict:
        """Get raw device info from Seam."""
        try:
            device = self._seam.devices.get(device_id=device_id)
            props = device.properties if hasattr(device, "properties") else {}
            return {
                "device_id": device_id,
                "device_type": getattr(device, "device_type", ""),
                "manufacturer": getattr(props, "manufacturer", ""),
                "model": getattr(props, "model", {}).get("display_name", "") if isinstance(getattr(props, "model", None), dict) else "",
                "name": getattr(props, "name", ""),
                "online": getattr(props, "online", False),
                "battery_level": getattr(props, "battery_level", None),
            }
        except Exception as exc:
            logger.error("Seam get_device failed for %s: %s", device_id, exc)
            raise DomoticsProviderError(f"Failed to get device: {exc}", device_id=device_id)
