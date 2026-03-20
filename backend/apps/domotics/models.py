from django.db import models

from common.models import TimeStampedModel


class SmartDevice(TimeStampedModel):
    class DeviceType(models.TextChoices):
        SMART_LOCK = "smart_lock", "Smart Lock"
        THERMOSTAT = "thermostat", "Thermostat"
        NOISE_SENSOR = "noise_sensor", "Noise Sensor"

    class Brand(models.TextChoices):
        AUGUST = "august", "August"
        SCHLAGE = "schlage", "Schlage"
        NEST = "nest", "Nest"
        ECOBEE = "ecobee", "Ecobee"
        MINUT = "minut", "Minut"

    class Status(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        ERROR = "error", "Error"
        SETUP = "setup", "Setup"

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="smart_devices",
    )
    device_type = models.CharField(max_length=20, choices=DeviceType.choices)
    brand = models.CharField(max_length=20, choices=Brand.choices)
    model_name = models.CharField(max_length=100, blank=True)
    external_device_id = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SETUP
    )
    api_credentials = models.TextField(blank=True)  # JSON encrypted
    config = models.JSONField(default=dict, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    battery_level = models.PositiveSmallIntegerField(null=True, blank=True)
    firmware_version = models.CharField(max_length=50, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["property", "device_type"]),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.device_type} - {self.brand})"


class LockAccessCode(TimeStampedModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"
        FAILED = "failed", "Failed"

    device = models.ForeignKey(
        SmartDevice,
        on_delete=models.CASCADE,
        related_name="access_codes",
        limit_choices_to={"device_type": "smart_lock"},
    )
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.CASCADE,
        related_name="lock_access_codes",
    )
    code = models.CharField(max_length=8)
    code_name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    activated_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"Code {self.code_name} for {self.reservation}"


class NoiseAlert(TimeStampedModel):
    class Severity(models.TextChoices):
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    device = models.ForeignKey(
        SmartDevice,
        on_delete=models.CASCADE,
        related_name="noise_alerts",
        limit_choices_to={"device_type": "noise_sensor"},
    )
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="noise_alerts",
    )
    decibel_level = models.DecimalField(max_digits=5, decimal_places=1)
    threshold_exceeded = models.BooleanField(default=False)
    severity = models.CharField(max_length=10, choices=Severity.choices)
    duration_seconds = models.PositiveIntegerField(default=0)
    alert_sent_to_owner = models.BooleanField(default=False)
    alert_sent_to_guest = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Noise alert {self.decibel_level}dB - {self.severity}"


class ThermostatLog(TimeStampedModel):
    class EventType(models.TextChoices):
        SETPOINT_CHANGE = "setpoint_change", "Setpoint Change"
        MODE_CHANGE = "mode_change", "Mode Change"
        CHECKIN_PRESET = "checkin_preset", "Check-in Preset"
        CHECKOUT_RESET = "checkout_reset", "Checkout Reset"

    class TriggeredBy(models.TextChoices):
        SYSTEM = "system", "System"
        GUEST = "guest", "Guest"
        OWNER = "owner", "Owner"

    device = models.ForeignKey(
        SmartDevice,
        on_delete=models.CASCADE,
        related_name="thermostat_logs",
        limit_choices_to={"device_type": "thermostat"},
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    temperature_set_f = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True
    )
    mode = models.CharField(max_length=20, blank=True)  # heat/cool/auto/off
    triggered_by = models.CharField(max_length=10, choices=TriggeredBy.choices)

    def __str__(self):
        return f"{self.event_type} - {self.temperature_set_f}\u00b0F"
