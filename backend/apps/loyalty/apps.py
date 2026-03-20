from django.apps import AppConfig


class LoyaltyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.loyalty"
    verbose_name = "Loyalty"

    def ready(self):
        from apps.hostaway.signals import reservation_cancelled

        from .signal_handlers import on_reservation_cancelled, on_reservation_checked_out

        # We listen to reservation_cancelled for point refunds.
        # For checkout, we listen to reservation_confirmed and check status inside,
        # because there is no separate "checked_out" signal — the hostaway module
        # fires reservation_confirmed for status transitions. The signal handler
        # checks reservation.status == 'checked_out' internally.
        reservation_cancelled.connect(on_reservation_cancelled)

        # NOTE: on_reservation_checked_out is called from process_checkout_loyalty
        # task which is triggered when a reservation transitions to checked_out.
        # It's also connected here for direct signal-based triggering.
        from apps.hostaway.signals import reservation_confirmed

        reservation_confirmed.connect(on_reservation_checked_out)
