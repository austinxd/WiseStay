from django.dispatch import Signal

# Fired when a reservation is confirmed (webhook or sync).
# sender = Reservation instance, kwargs: created (bool)
reservation_confirmed = Signal()

# Fired when a reservation is cancelled.
# sender = Reservation instance
reservation_cancelled = Signal()

# Fired when a reservation's dates change.
# sender = Reservation instance, kwargs: old_check_in, old_check_out
reservation_dates_changed = Signal()
