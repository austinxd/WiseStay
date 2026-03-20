from django.apps import AppConfig


class DomoticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.domotics"
    verbose_name = "Domotics"

    def ready(self):
        from apps.hostaway.signals import (
            reservation_cancelled,
            reservation_confirmed,
            reservation_dates_changed,
        )

        from .signal_handlers import (
            on_reservation_cancelled_domotics,
            on_reservation_confirmed_domotics,
            on_reservation_dates_changed_domotics,
        )

        reservation_confirmed.connect(on_reservation_confirmed_domotics)
        reservation_cancelled.connect(on_reservation_cancelled_domotics)
        reservation_dates_changed.connect(on_reservation_dates_changed_domotics)
